"""
app.py
======
OmniOS command-line demo.

Accepts natural-language commands, routes them through the classifier/
router, executes supported local actions, and prints the result.
Type 'exit' or 'quit' to stop.
"""

from __future__ import annotations

from typing import Optional, Tuple

from core.schemas import ExecutionResult, Route, RoutingDecision, TaskRequest
from router.task_router import route
from actions.registry import execute


_BANNER = """\
╔══════════════════════════════════════════╗
║              OmniOS  v0.1                ║
║   Local Windows Action Layer — Demo      ║
╚══════════════════════════════════════════╝
Type a command, 'voice' to speak, or 'exit' to quit.

Examples:
  calculate 10 + 5 * 2
  open notepad
  open https://example.com
  find report.pdf on my computer
  summarize my meeting notes
  voice
"""

_SEPARATOR = "─" * 44


def _display(decision: RoutingDecision, result: Optional[ExecutionResult] = None) -> None:
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


def process_command(user_input: str) -> Tuple[RoutingDecision, Optional[ExecutionResult]]:
    """Process a natural-language command through the OmniOS pipeline.

    Wraps raw input into a TaskRequest, routes it to determine intent and
    target action, dispatches local actions to the action registry with
    safety checks, and displays the result.
    """
    decision = route(TaskRequest(raw_input=user_input))

    if decision.route == Route.LOCAL:
        result = execute(decision.action_name, decision.validated_args or {})
        _display(decision, result)
    else:
        result = None
        _display(decision)

    return decision, result


def _handle_voice_input() -> Optional[str]:
    """Capture a voice command via speech recognition."""
    try:
        from test_router_voice import listen_for_command
    except ImportError as e:
        print(f"  Voice error: speech_recognition module unavailable ({e}).")
        return None

    print("Listening for voice command...")
    text = listen_for_command()
    if text:
        print(f"  (heard: \"{text}\")")
    return text


def run(voice_mode: bool = False) -> None:
    print(_BANNER)
    while True:
        try:
            if voice_mode:
                print("OmniOS (voice)> Speak a command (or say 'exit')...")
                user_input = _handle_voice_input()
                if user_input is None:
                    continue
            else:
                user_input = input("OmniOS> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not voice_mode and user_input.lower() in {"voice", "speak"}:
            voice_text = _handle_voice_input()
            if not voice_text:
                continue
            if voice_text.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break
            process_command(voice_text)
            continue

        process_command(user_input)


if __name__ == "__main__":
    import sys
    voice = "--voice" in sys.argv
    run(voice_mode=voice)
