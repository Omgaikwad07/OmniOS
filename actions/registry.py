"""
actions/registry.py
===================
Central dispatch table for all approved local actions in OmniOS.

Responsibilities
----------------
* Map action names (as produced by the router) to handler functions.
* Validate that required arguments are present and well-formed before
  invoking any handler.
* Reject unknown action names and malformed argument dicts.
* Return the handler's ``ExecutionResult`` unchanged.

Non-responsibilities
--------------------
* Intent classification — that is the router's job.
* LOCAL vs LLM routing — that is the router's job.
* Calling an LLM — never done here for supported local actions.
"""

from __future__ import annotations

from typing import Any, Dict

from actions.apps import open_app
from actions.calculator import calculate
from actions.file_search import file_search
from actions.open_file import open_file
from actions.urls import open_url
from core.schemas import ExecutionResult, ResultStatus

# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
# Each entry: action_name -> (handler, required_args, optional_args)
# required_args: keys that MUST be present and non-empty
# optional_args: keys that MAY be present; all others are rejected

_REGISTRY: Dict[str, tuple] = {
    "open_app":    (open_app,     ("app_name",),  ()),
    "open_url":    (open_url,     ("url",),        ()),
    "calculate":   (calculate,    ("expression",), ()),
    "file_search": (file_search,  ("query",),      ("root", "location")),
    "open_file":   (open_file,    ("filename",),   ("root",)),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(action_name: str, args: Dict[str, Any]) -> ExecutionResult:
    """Validate and dispatch a local action.

    Parameters
    ----------
    action_name : str
        One of ``open_app``, ``open_url``, ``calculate``, ``file_search``.
    args : dict
        Arguments extracted by the router (``RoutingDecision.validated_args``).

    Returns
    -------
    ExecutionResult
        The result from the handler, or an ERROR/REFUSED result when
        validation fails.
    """
    if not action_name or not isinstance(action_name, str):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="action_name must be a non-empty string.",
        )

    entry = _REGISTRY.get(action_name.strip())
    if entry is None:
        supported = ", ".join(sorted(_REGISTRY))
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=(
                f"Unknown action '{action_name}'. "
                f"Supported actions: {supported}."
            ),
        )

    handler, required, optional = entry

    if not isinstance(args, dict):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"args must be a dict, got {type(args).__name__}.",
        )

    # Check for unexpected keys.
    allowed_keys = set(required) | set(optional)
    unexpected = set(args) - allowed_keys
    if unexpected:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=(
                f"Unexpected argument(s) for '{action_name}': "
                f"{', '.join(sorted(unexpected))}."
            ),
        )

    # Check required keys are present and non-empty.
    for key in required:
        val = args.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            return ExecutionResult(
                status=ResultStatus.ERROR,
                error=f"Missing or empty required argument '{key}' for '{action_name}'.",
            )

    # Dispatch — pass only the args the handler accepts.
    if action_name == "file_search":
        return handler(
            query=args["query"],
            root=args.get("root"),
        )

    if action_name == "open_file":
        return handler(
            filename=args["filename"],
            root=args.get("root"),
        )

    # All other handlers take exactly one positional argument.
    primary_key = required[0]
    return handler(args[primary_key])
