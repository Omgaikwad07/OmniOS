# OmniOS Architecture

This document describes the architecture as it is currently implemented.
Planned but not-yet-implemented components are clearly marked.

---

## Overview

OmniOS is a Windows desktop assistant. A user types a natural-language
command; the system classifies it, routes it, and either executes a local
action or (in future) forwards it to an LLM.

```
User input (text)
      │
      ▼
┌─────────────────┐
│  classifier.py  │  Rule-based intent classification (no LLM)
│  (router/)      │  Returns: Intent + confidence
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ task_router.py  │  Maps intent → Route + action_name + validated_args
│  (router/)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 LOCAL       LLM / NONE
    │         │
    ▼         └──► Not yet implemented
┌─────────────────┐
│  registry.py    │  Validates args, dispatches to handler
│  (actions/)     │
└────────┬────────┘
         │
    ┌────┼────┬────────┐
    ▼    ▼    ▼        ▼
 apps  urls  calc  file_search
```

---

## Implemented modules

### `core/schemas.py`
Shared dataclasses and enums used by every layer:
- `TaskRequest` — raw user input
- `RoutingDecision` — classifier + router output
- `ExecutionResult` — action handler output
- `Intent`, `Route`, `ResultStatus` enums

### `router/classifier.py`
Rule-based intent classifier. Uses compiled regexes and keyword tables.
No LLM call. Returns `ClassificationResult` with intent and confidence.

Recognised intents: `OPEN_APP`, `OPEN_URL`, `CALCULATE`, `FILE_SEARCH`,
`LLM_TASK`, `UNKNOWN`.

### `router/task_router.py`
Converts a `ClassificationResult` into a `RoutingDecision`. Extracts
action arguments from the raw input (app name, URL, expression, query).
Never executes anything.

### `actions/registry.py`
Central dispatch table. Validates action name and arguments, then calls
the appropriate handler. Returns `ExecutionResult` unchanged.

### `actions/apps.py`
Launches allowlisted Windows applications via `subprocess.Popen`.
No `shell=True`. Allowlist: `calculator`, `notepad`, `paint`, `wordpad`,
`explorer`, `cmd`, `taskmgr`, `task manager`, `snipping tool`.

### `actions/urls.py`
Opens URLs in the system default browser via `webbrowser.open`.
Accepts `http` and `https` only. Blocks `file`, `javascript`, `data`,
`ftp`, `ftps`, `mailto`, `vbscript`.

### `actions/calculator.py`
Evaluates arithmetic expressions using Python's `ast` module.
No `eval()` or `exec()`. Supports `+`, `-`, `*`, `/`, `%`, `**`, `()`.
Integer exponentiation is bounded to prevent resource exhaustion.

### `actions/file_search.py`
Searches for files by name within the user's home directory.
Path traversal is blocked via `os.path.realpath` containment checks.
File contents are never read.

### `core/config.py`
Static configuration: app allowlist, file search root and limits.

### `core/exceptions.py`
Project-wide exception hierarchy: `OmniOSError`, `UnsupportedActionError`,
`ValidationError`.

### `app.py`
CLI entry point. Reads user input, calls `route()`, calls `execute()` for
LOCAL routes, and prints a structured result.

---

## Stub modules (not yet implemented)

| Module | Purpose | Status |
|---|---|---|
| `agent/llm_client.py` | LLM API integration | Stub |
| `agent/pdf_summarizer.py` | PDF summarisation via LLM | Stub |
| `context/context_manager.py` | Ambient context (active window, etc.) | Stub |
| `context/privacy_policy.py` | Data handling policy enforcement | Stub |
| `safety/confirmations.py` | User confirmation prompts for risky actions | Stub |
| `safety/risk_policy.py` | Risk scoring for actions | Stub |

---

## Data flow (LOCAL action)

```
user_input: "calculate 10 + 5"

1. route(TaskRequest(raw_input="calculate 10 + 5"))
   → RoutingDecision(
       intent=CALCULATE,
       route=LOCAL,
       action_name="calculate",
       validated_args={"expression": "10 + 5"},
       confidence=0.90
     )

2. execute("calculate", {"expression": "10 + 5"})
   → ExecutionResult(status=SUCCESS, output=15, used_llm=False)
```

---

## Data flow (LLM task — not yet implemented)

```
user_input: "summarize my meeting notes"

1. route(TaskRequest(...))
   → RoutingDecision(intent=LLM_TASK, route=LLM, action_name=None)

2. LLM layer (not implemented) — app.py displays a clear message.
```

---

## Security properties

- No `eval()`, `exec()`, or `shell=True` anywhere in the action layer.
- Application launching uses an explicit allowlist; arbitrary paths are rejected.
- URL opening validates scheme before calling `webbrowser.open`.
- Calculator uses AST walking against an explicit node allowlist.
- File search uses `os.path.realpath` containment; traversal guard runs
  before any existence check.
- All local actions return `used_llm=False`.

---

## Test coverage

```
tests/test_router.py      — 63 tests  (Person 1 scope)
tests/test_actions.py     — 89 tests  (Person 2 scope)
tests/test_safety.py      — 37 tests  (Person 2 scope)
tests/test_end_to_end.py  — 10 tests  (integration)
tests/test_app.py         — 9  tests  (CLI entry point)
                            ─────────
Total                       208 tests
```
