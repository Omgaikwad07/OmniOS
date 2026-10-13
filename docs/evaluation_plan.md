# Evaluation Plan — OmniOS

This document describes how OmniOS will be evaluated, what has been
implemented, and what remains planned. It does not claim results that
have not been measured.

---

## 1. What is being evaluated

OmniOS is evaluated on two axes:

1. **Correctness** — does each component do what its contract says?
2. **Safety** — does the system reject dangerous inputs before any
   system call is made?

---

## 2. Implemented and testable now

### 2.1 Intent classification

The rule-based classifier is evaluated by `tests/test_router.py`
(63 tests). Metrics:

- Correct intent for all supported command patterns
- Confidence ≥ 0.70 for keyword matches, ≥ 0.85 for regex matches
- `UNKNOWN` returned for unrecognised input (no false execution)
- Deterministic — same input always produces the same output

### 2.2 Task routing

Evaluated by `tests/test_router.py` and `tests/test_end_to_end.py`.

- LOCAL route for `OPEN_APP`, `OPEN_URL`, `CALCULATE`, `FILE_SEARCH`
- LLM route for `LLM_TASK`
- NONE route for `UNKNOWN`
- Correct argument extraction for each intent

### 2.3 Local action layer

Evaluated by `tests/test_actions.py` (89 tests) and
`tests/test_safety.py` (37 tests).

**Calculator:**
- Correct results for all six operators and parentheses
- Division/modulo by zero → `ERROR`
- Blocked AST nodes → `REFUSED`
- Integer exponentiation limits enforced (base ≤ 1,000,000; exp ≤ 1,000)
- `9**9**9` refused before any large integer is constructed

**Application launcher:**
- All 9 allowlisted apps → `SUCCESS` (mocked)
- Unknown app → `REFUSED`
- Missing executable → `ERROR`
- `shell=True` never used

**URL opener:**
- `http`/`https` → `SUCCESS` (mocked)
- 7 blocked schemes → `REFUSED`
- No host → `REFUSED`

**File search:**
- Filename match, partial match, case-insensitive match → `SUCCESS`
- Path traversal → `REFUSED` (guard runs before existence check)
- Missing directory → `ERROR`
- Results bounded by depth and count limits

### 2.4 Integration

Evaluated by `tests/test_end_to_end.py` (10 tests).

- Natural-language input → router → registry → correct result
- LLM tasks do not reach the local registry
- `used_llm=False` for all local actions

### 2.5 CLI entry point

Evaluated by `tests/test_app.py` (9 tests).

- Clean exit on `exit`/`quit`/`Ctrl+C`
- LOCAL actions dispatched and result displayed
- LLM route handled gracefully (no crash, no fake success)
- NONE route handled gracefully
- Empty input ignored

---

## 3. Current test results

```
python -m pytest tests/ -q
208 passed
```

All tests are deterministic. No network access, no real application
launches, no API keys required.

---

## 4. Not yet implemented — cannot be evaluated

| Component | Reason |
|---|---|
| LLM integration | No API key configured; `agent/llm_client.py` is a stub |
| Voice interface | Not started |
| GUI | Not started |
| Context/memory | `context/context_manager.py` is a stub |
| PDF summarisation | `agent/pdf_summarizer.py` is a stub |
| Risk policy / confirmations | `safety/` modules are stubs |

These components will be evaluated when implemented. No evaluation
results are claimed for them here.

---

## 5. Planned evaluation criteria (future)

When the LLM integration is implemented, evaluation will include:

- Accuracy of LLM responses on a fixed set of test prompts
- Latency (time from user input to displayed result)
- Graceful degradation when the LLM API is unavailable
- Privacy: no user data sent to the LLM for LOCAL-routed tasks

When the voice interface is implemented:

- Word error rate on a fixed set of spoken commands
- Correct intent classification from transcribed text

---

## 6. How to run the evaluation

```
# Automated tests
python -m pytest tests/ -q

# Manual demo
python app.py
```

No additional setup is required for the automated tests.
