"""
ui/state.py
===========
Lightweight observable application state shared across UI components.

Pattern: subscriber callbacks are registered via ``subscribe()``.
All writes to state (set_processing, update_result, clear_activity) call
``notify()`` which fires every registered callback on the caller's thread.
Callers that write from a background thread MUST dispatch via
``root.after(0, lambda: state.update_result(...))``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AppState:
    """Mutable application state.

    Thread safety: read anywhere; write only from the main Tk thread.
    Background workers must post updates via ``widget.after(0, ...)``.
    """

    # Last pipeline output (None until first command is submitted)
    last_decision: Any = None   # Optional[RoutingDecision]
    last_result: Any = None     # Optional[ExecutionResult]

    # True while a command is being processed
    is_processing: bool = False

    # Recent activity log — newest entry first, max 20 entries
    activity: list[dict[str, str]] = field(default_factory=list)

    # Internal subscriber list (not serialised)
    _listeners: list[Callable[[], None]] = field(
        default_factory=list, repr=False
    )

    # ── Subscription ─────────────────────────────────────────────────────────

    def subscribe(self, callback: Callable[[], None]) -> None:
        """Register a callback to be fired on every state change."""
        self._listeners.append(callback)

    def notify(self) -> None:
        """Fire every registered callback (silently ignores errors)."""
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                pass

    # ── Mutations ────────────────────────────────────────────────────────────

    def set_processing(self, value: bool) -> None:
        """Toggle the processing flag and notify subscribers."""
        self.is_processing = value
        self.notify()

    def update_result(
        self,
        decision: Any,
        result: Any,
        command: str,
    ) -> None:
        """Store a completed pipeline result and add an activity entry."""
        self.last_decision = decision
        self.last_result = result
        self.is_processing = False

        entry: dict[str, str] = {
            "command": command[:60] + ("…" if len(command) > 60 else ""),
            "intent":  decision.intent.value if decision else "–",
            "status":  result.status.value if result else "–",
        }
        self.activity.insert(0, entry)
        if len(self.activity) > 20:
            self.activity.pop()

        self.notify()

    def clear_activity(self) -> None:
        """Clear the recent activity log and notify subscribers."""
        self.activity.clear()
        self.notify()
