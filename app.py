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
import re
import sys
from typing import Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import core.config as _cfg
from core.schemas import ExecutionResult, ResultStatus, Route, RoutingDecision, TaskRequest
from router.task_router import route
from actions.registry import execute


_BANNER = """\
============================================
              OmniOS  v0.1                  
   Local Windows Action Layer — Demo        
============================================
Type a command, 'voice' to speak, or 'exit' to quit.

Examples:
  calculate 10 + 5 * 2
  open notepad
  open https://example.com
  find/open notes.txt on my computer
  summarize my meeting notes
  voice
"""

_SEPARATOR = "-" * 44


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


# Allowed file extensions — used to detect open-file intent in process_command.
_FILE_EXTS = _cfg.FILE_OPEN_ALLOWED_EXTENSIONS


def _extract_filename_from_input(user_input: str) -> Optional[str]:
    """Return the filename (with allowed extension) from user_input, or None.

    Handles multi-word filenames like 'omnios synopsis.pdf' by collecting
    all tokens from after the leading verb up to and including the token
    that carries the allowed extension.
    """
    tokens = user_input.split()
    for i, token in enumerate(tokens):
        clean = token.strip(".,;'\"")
        _, ext = os.path.splitext(clean)
        if ext.lower() in _FILE_EXTS:
            verb_re = re.match(
                r"^(?:open|find|show|view|locate|search(?:\s+for)?)\s+",
                user_input, re.IGNORECASE,
            )
            start = verb_re.end() if verb_re else 0
            candidate = " ".join(tokens)[start:]
            # Trim trailing location phrases.
            candidate = re.sub(
                r"\s+(?:on|in|from)\s+(?:my\s+|the\s+)?(?:computer|pc|laptop|"
                r"desktop|documents|downloads|files|disk|drive)\s*$",
                "", candidate, flags=re.IGNORECASE,
            ).strip()
            return candidate if candidate else None
    return None


def _handle_llm_task(user_input: str) -> ExecutionResult:
    """Execute an LLM task (either PDF summarization or general language reasoning)."""
    # Check if a PDF file was targeted for summarization
    pdf_candidate = None
    for token in user_input.split():
        clean = token.strip(".,;'\"")
        if clean.lower().endswith(".pdf"):
            pdf_candidate = clean
            break

    if pdf_candidate:
        from agent.pdf_summarizer import summarize_pdf
        target_path = pdf_candidate
        if not os.path.exists(target_path):
            search_res = execute("file_search", {"query": os.path.basename(pdf_candidate)})
            if search_res.status == ResultStatus.SUCCESS and search_res.output:
                target_path = search_res.output[0]
        return summarize_pdf(target_path, consent_to_external_processing=True)

    # General LLM reasoning task
    from agent.llm_client import generate_text
    try:
        output = generate_text(prompt=user_input)
        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            output=output,
            error=None,
            used_llm=True,
        )
    except Exception as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            output=None,
            error=str(exc),
            used_llm=True,
        )


def process_command(user_input: str) -> Tuple[RoutingDecision, Optional[ExecutionResult]]:
    """Process a natural-language command through the OmniOS pipeline.

    Wraps raw input into a TaskRequest, routes it to determine intent and
    target action, dispatches local actions to the action registry with
    safety checks, and displays the result.

    Open-file detection (3 types of 'open'):
    1. open <app>       → OPEN_APP  → open_app
    2. open <url>       → OPEN_URL  → open_url
    3. open <file.ext>  → redirected to open_file regardless of router intent

    The router cannot distinguish case 3 from cases 1/2 without knowing the
    filesystem, so process_command intercepts misclassified results here.
    find/search <file.ext> always goes to file_search (not open_file).
    """
    decision = route(TaskRequest(raw_input=user_input))

    if decision.route == Route.LOCAL:
        action = decision.action_name
        args = decision.validated_args or {}

        # --- Open-file interception ---
        # Detect when the user said "open <something.ext>" but the router
        # classified it as OPEN_APP (app_name has an extension) or OPEN_URL
        # (router prepended https:// to a bare filename).
        # Only intercept when the leading verb is open/view/show — never for
        # find/search/locate which must always go to file_search.
        is_open_verb = bool(re.match(
            r"^(?:open|view|show)\b", user_input.strip(), re.IGNORECASE
        ))

        if is_open_verb:
            filename = _extract_filename_from_input(user_input)
            if filename:
                action = "open_file"
                args = {"filename": filename}

        # --- find/search with allowed extension → file_search (not open_file) ---
        elif action == "file_search":
            # Already correct — no redirect needed.
            pass

        result = execute(action, args)
        _display(decision, result)
    elif decision.route == Route.LLM:
        if not _cfg.GROQ_API_KEY:
            result = None
            _display(decision)
        else:
            result = _handle_llm_task(user_input)
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
