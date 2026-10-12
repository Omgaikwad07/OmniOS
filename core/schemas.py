"""
core/schemas.py
===============
Shared data contracts for OmniOS.

These models define the communication protocol between the classifier,
router, action handlers, and the LLM agent layer.  Every module in the
project should import these types rather than inventing ad-hoc dicts.

Design decisions
----------------
* **stdlib only** – uses `dataclasses` and `enum` so there are zero
  third-party dependencies.  If the team later adopts Pydantic, migration
  is straightforward because the field names and semantics stay the same.
* **Enums for closed sets** – `Intent`, `Route`, and `ResultStatus` are
  enums so that typos are caught at import time, not at runtime.
* **Optional fields default to None** – downstream handlers can check
  presence without try/except.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Intent(Enum):
    """Intents the classifier can assign to a user request.

    Members
    -------
    OPEN_APP     – Launch a desktop application (e.g. "open Notepad").
    OPEN_URL     – Open a URL in the default browser.
    CALCULATE    – Evaluate a mathematical expression.
    FILE_SEARCH  – Search for a file on the local filesystem.
    LLM_TASK     – A task that requires language-model reasoning
                   (summarisation, explanation, creative writing, etc.).
    UNKNOWN      – The classifier could not determine a clear intent.
    """

    OPEN_APP = "OPEN_APP"
    OPEN_URL = "OPEN_URL"
    CALCULATE = "CALCULATE"
    FILE_SEARCH = "FILE_SEARCH"
    LLM_TASK = "LLM_TASK"
    UNKNOWN = "UNKNOWN"


class Route(Enum):
    """Execution route for a classified task.

    Members
    -------
    LOCAL – The task can be handled entirely on the local machine
            (app launch, URL open, calculator, file search).
    LLM   – The task must be forwarded to an LLM for reasoning.
    NONE  – The router could not determine a safe route (e.g. UNKNOWN
            intent or ambiguous request).
    """

    LOCAL = "LOCAL"
    LLM = "LLM"
    NONE = "NONE"


class ResultStatus(Enum):
    """Outcome status of an executed task.

    Members
    -------
    SUCCESS – The action completed without errors.
    ERROR   – The action failed; see ``error`` for details.
    REFUSED – The safety layer or risk policy blocked the action.
    PENDING – The action was accepted but has not finished yet.
    """

    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    REFUSED = "REFUSED"
    PENDING = "PENDING"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TaskRequest:
    """Represents a raw, incoming user request.

    Attributes
    ----------
    raw_input : str
        The original natural-language string from the user.
    context : dict
        Optional ambient context (e.g. current directory, active window).
        Defaults to an empty dict.  The context module (Member 4) will
        populate this; for now it is a placeholder.
    """

    raw_input: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """The router's decision about how to handle a classified task.

    Attributes
    ----------
    intent : Intent
        The classified intent of the user's request.
    route : Route
        Where the task should be executed (LOCAL, LLM, or NONE).
    confidence : float
        A 0.0 – 1.0 score indicating classification confidence.
    explanation : str
        Human-readable rationale for the routing decision.
    action_name : str | None
        The registered action handler to invoke (e.g. "open_app",
        "calculate").  ``None`` when the route is LLM or NONE.
    validated_args : dict | None
        Arguments extracted from the user request that have been
        validated for the target action handler.  ``None`` when not
        applicable.
    """

    intent: Intent
    route: Route
    confidence: float
    explanation: str
    action_name: Optional[str] = None
    validated_args: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionResult:
    """The result returned after a task has been executed.

    Attributes
    ----------
    status : ResultStatus
        Whether the execution succeeded, failed, was refused, or is
        pending.
    output : Any
        The primary output payload (string, dict, list, etc.).
    error : str | None
        A human-readable error message when ``status`` is ERROR.
    used_llm : bool
        Whether an LLM call was made during execution.
    """

    status: ResultStatus
    output: Any = None
    error: Optional[str] = None
    used_llm: bool = False
