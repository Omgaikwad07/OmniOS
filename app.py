"""
app.py
======
OmniOS command-line demo.

Accepts natural-language commands, routes them through the classifier/
router, executes supported local actions, and prints the result.
Type 'exit' or 'quit' to stop.
"""

from __future__ import annotations

import os

import core.config as _cfg
from core.schemas import Route, TaskRequest
from router.task_router import route
from actions.registry import execute


_BANNER = """\
╔══════════════════════════════════════════╗
║              OmniOS  v0.1                ║
║   Local Windows Action Layer — Demo      ║
╚══════════════════════════════════════════╝
Type a command, or 'exit' to quit.

Examples:
  calculate 10 + 5 * 2
  open notepad
  open https://example.com
  find report.pdf on my computer
  summarize my meeting notes
"""

_SEPARATOR = "─" * 44


def _display(decision, result=None) -> None:
    print(_SEPARATOR)
    print(f"  Intent   : {decision.intent.value}")
    print(f"  Route    : {decision.route.value}")
    print(f"  Confidence: {decision.confidence:.0%}")

    if result is None:
        # LLM or NONE route — no local execution
        if decision.route == Route.LLM:
            print("  Result   : LLM integration not yet implemented.")
            print("             (No API key configured; no call was made.)")
        else:
            print("  Result   : Could not determine a supported action.")
            print("             Try: calculate, open <app>, open <url>,")
            print("             or: find <filename>")
    else:
        print(f"  Status   : {result.status.value}")
        if result.output is not None:
            print(f"  Output   : {result.output}")
        if result.error:
            print(f"  Error    : {result.error}")
        print(f"  Used LLM : {result.used_llm}")
    print(_SEPARATOR)


def run() -> None:
    print(_BANNER)
    while True:
        try:
            user_input = input("OmniOS> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        decision = route(TaskRequest(raw_input=user_input))

        if decision.route == Route.LOCAL:
            # If the router classified this as FILE_SEARCH but the query
            # looks like an exact filename with an allowed extension, try
            # open_file first so the file is opened rather than just found.
            action = decision.action_name
            args = decision.validated_args or {}
            if action == "file_search":
                query = args.get("query", "")
                _, ext = os.path.splitext(query)
                if ext.lower() in _cfg.FILE_OPEN_ALLOWED_EXTENSIONS:
                    action = "open_file"
                    args = {"filename": query}
            result = execute(action, args)
            _display(decision, result)
        else:
            _display(decision)


if __name__ == "__main__":
    run()
