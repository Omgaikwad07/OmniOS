"""
ui/state.py
===========
Observable application state shared across UI components.

Pattern: subscriber callbacks are registered via ``subscribe()``; every
mutation calls ``notify()`` on the caller's thread.  Writes MUST happen on the
Tk main thread — background workers post via ``root.after(0, ...)``.

Outcome model
-------------
A finished command is exactly one of ``Outcome``; the UI never has to guess
from ``result is None``:

    SUCCESS         backend returned ResultStatus.SUCCESS with output
    EMPTY           backend succeeded but there was nothing to show
                    (e.g. a file search with zero matches)
    ERROR           backend returned ResultStatus.ERROR (or raised)
    REFUSED         the safety layer refused the action
    PENDING         backend returned ResultStatus.PENDING
    LLM_UNAVAILABLE routed to the LLM but no result exists (no API key)
    NO_ACTION       the router could not pick a supported action

``is_processing`` and ``current`` are cleared the moment a new command starts,
so a previous execution can never leak into the next one.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

ACTIVITY_LIMIT = 20


class Outcome(enum.Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    REFUSED = "REFUSED"
    PENDING = "PENDING"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    NO_ACTION = "NO_ACTION"


def classify_outcome(decision: Any, result: Any) -> Outcome:
    """Map a backend ``(decision, result)`` pair onto exactly one Outcome."""
    if result is None:
        route = getattr(getattr(decision, "route", None), "value", None)
        return Outcome.LLM_UNAVAILABLE if route == "LLM" else Outcome.NO_ACTION

    status = getattr(getattr(result, "status", None), "value", None)
    if status == "SUCCESS":
        out = result.output
        if out is None or (isinstance(out, (list, tuple, str)) and len(out) == 0):
            return Outcome.EMPTY
        return Outcome.SUCCESS
    if status == "REFUSED":
        return Outcome.REFUSED
    if status == "PENDING":
        return Outcome.PENDING
    return Outcome.ERROR


@dataclass(frozen=True)
class Execution:
    """One completed command and everything the UI shows about it."""

    command: str
    decision: Any            # RoutingDecision
    result: Any              # Optional[ExecutionResult]
    outcome: Outcome

    @property
    def item_count(self) -> Optional[int]:
        """Number of items — only when the real output is a list/tuple."""
        out = getattr(self.result, "output", None)
        if self.outcome is Outcome.SUCCESS and isinstance(out, (list, tuple)):
            return len(out)
        return None

    @property
    def used_llm(self) -> bool:
        return bool(getattr(self.result, "used_llm", False))


@dataclass
class AppState:
    """Mutable application state (main-thread writes only)."""

    # The execution currently on display (None while idle / processing).
    current: Optional[Execution] = None
    # Command being executed right now (None when idle).
    running_command: Optional[str] = None
    is_processing: bool = False

    # Newest first, max ACTIVITY_LIMIT entries.
    activity: list[dict[str, str]] = field(default_factory=list)

    _listeners: list[Callable[[], None]] = field(default_factory=list, repr=False)

    # ── Back-compat read accessors (older components used these) ────────────
    @property
    def last_decision(self) -> Any:
        return self.current.decision if self.current else None

    @property
    def last_result(self) -> Any:
        return self.current.result if self.current else None

    # ── Subscription ────────────────────────────────────────────────────────
    def subscribe(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:  # one broken listener must not starve the rest
                import traceback
                traceback.print_exc()

    # ── Mutations ───────────────────────────────────────────────────────────
    def begin(self, command: str) -> None:
        """A command started: drop the previous execution immediately."""
        self.current = None
        self.running_command = command
        self.is_processing = True
        self.notify()

    def set_processing(self, value: bool) -> None:
        """Compatibility shim: ``True`` starts an anonymous run."""
        if value:
            self.begin(self.running_command or "")
            return
        self.is_processing = False
        self.running_command = None
        self.notify()

    def update_result(self, decision: Any, result: Any, command: str) -> Execution:
        """Store a completed pipeline result and record activity."""
        outcome = classify_outcome(decision, result)
        execution = Execution(command, decision, result, outcome)
        self.current = execution
        self.is_processing = False
        self.running_command = None
        self.activity.insert(0, make_activity_entry(execution))
        del self.activity[ACTIVITY_LIMIT:]
        self.notify()
        return execution

    def clear_activity(self) -> None:
        self.activity.clear()
        self.notify()


# ---------------------------------------------------------------------------
# Activity entries
# ---------------------------------------------------------------------------

_ACTIVITY_LABEL = {
    Outcome.SUCCESS: ("SUCCESS", "ok"),
    Outcome.EMPTY: ("NO MATCHES", "warn"),
    Outcome.ERROR: ("ERROR", "bad"),
    Outcome.REFUSED: ("REFUSED", "warn"),
    Outcome.PENDING: ("PENDING", "warn"),
    Outcome.LLM_UNAVAILABLE: ("NOT CONFIGURED", "bad"),
    Outcome.NO_ACTION: ("NO ACTION", "warn"),
}


def make_activity_entry(execution: Execution, now: Optional[datetime] = None) -> dict[str, str]:
    """Build one Recent Activity record from a real execution."""
    now = now or datetime.now()
    intent = getattr(getattr(execution.decision, "intent", None), "value", "UNKNOWN")
    if execution.outcome is Outcome.LLM_UNAVAILABLE:
        intent = "LLM"
    label, tone = _ACTIVITY_LABEL[execution.outcome]
    cmd = execution.command
    return {
        "command": cmd[:60] + ("…" if len(cmd) > 60 else ""),
        "intent": intent,
        "status": label,
        "tone": tone,                       # ok | warn | bad
        "time": now.strftime("%I:%M %p"),   # e.g. 02:14 AM
    }
