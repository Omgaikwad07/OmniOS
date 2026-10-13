# Module Contracts — OmniOS

This document describes the public contracts for every module in the
OmniOS Windows Action Layer (Person 2 scope).  It is the authoritative
reference for how the router hands off to the action layer and what
callers can expect in return.

---

## 1. Shared schemas (`core/schemas.py`)

All modules communicate through these dataclasses.  Import them instead
of inventing ad-hoc dicts.

### `TaskRequest`
| Field | Type | Description |
|---|---|---|
| `raw_input` | `str` | Original natural-language string from the user |
| `context` | `dict` | Optional ambient context (populated by Person 4) |

### `RoutingDecision`
| Field | Type | Description |
|---|---|---|
| `intent` | `Intent` | Classified intent |
| `route` | `Route` | `LOCAL`, `LLM`, or `NONE` |
| `confidence` | `float` | 0.0–1.0 classification confidence |
| `explanation` | `str` | Human-readable rationale |
| `action_name` | `str \| None` | Registry key to invoke for LOCAL routes |
| `validated_args` | `dict \| None` | Arguments extracted by the router |

### `ExecutionResult`
| Field | Type | Description |
|---|---|---|
| `status` | `ResultStatus` | `SUCCESS`, `ERROR`, `REFUSED`, or `PENDING` |
| `output` | `Any` | Primary result payload |
| `error` | `str \| None` | Human-readable error message |
| `used_llm` | `bool` | Always `False` for local actions |

---

## 2. Action registry (`actions/registry.py`)

### `execute(action_name, args) -> ExecutionResult`

Single entry point for all local action dispatch.

**Registered actions:**

| `action_name` | Required args | Optional args |
|---|---|---|
| `open_app` | `app_name` | — |
| `open_url` | `url` | — |
| `calculate` | `expression` | — |
| `file_search` | `query` | `root`, `location` |

`location` is router metadata forwarded from `validated_args`; it is
accepted but not passed to the handler.

**Validation pipeline:**
1. `action_name` must be a non-empty string — else `ERROR`
2. `action_name` must be in the registry — else `REFUSED` (lists supported actions)
3. `args` must be a `dict` — else `ERROR`
4. No unexpected keys — else `REFUSED`
5. Required keys must be present and non-empty — else `ERROR`
6. Delegates to handler; returns its `ExecutionResult` unchanged

**The registry never classifies intents, chooses LOCAL vs LLM, or calls an LLM.**

---

## 3. Application launcher (`actions/apps.py`)

### `open_app(app_name) -> ExecutionResult`

Launches an approved Windows desktop application.

**Allowlisted applications** (case-insensitive):

| Name | Executable |
|---|---|
| `calculator` | `%SystemRoot%\System32\calc.exe` |
| `notepad` | `%SystemRoot%\System32\notepad.exe` |
| `paint` | `%SystemRoot%\System32\mspaint.exe` |
| `wordpad` | `%ProgramFiles%\Windows NT\Accessories\wordpad.exe` |
| `explorer` | `%SystemRoot%\System32\explorer.exe` |
| `cmd` | `%SystemRoot%\System32\cmd.exe` |
| `taskmgr` / `task manager` | `%SystemRoot%\System32\Taskmgr.exe` |
| `snipping tool` | `%SystemRoot%\System32\SnippingTool.exe` |

**Return values:**
- `SUCCESS` — process started
- `REFUSED` — name not in allowlist
- `ERROR` — executable missing or OS launch failure

**Security:** `subprocess.Popen` is called with an explicit list (no
`shell=True`).  Arbitrary paths and shell injection strings are rejected
by the allowlist lookup before any process is created.

---

## 4. URL opener (`actions/urls.py`)

### `open_url(url) -> ExecutionResult`

Opens a URL in the system default browser.

**Accepted schemes:** `http`, `https`

**Rejected schemes (REFUSED):** `file`, `javascript`, `data`, `ftp`,
`ftps`, `mailto`, `vbscript`, and any other non-http/https scheme.

**Additional validation:**
- URL must have a non-empty host (`https://` alone is rejected)
- Bare strings with no scheme are rejected

**Return values:**
- `SUCCESS` — browser invoked
- `REFUSED` — disallowed scheme or malformed URL
- `ERROR` — empty input or browser launch failure

**Security:** `webbrowser.open` is used; no shell command is constructed.

---

## 5. Calculator (`actions/calculator.py`)

### `calculate(expression) -> ExecutionResult`

Evaluates a safe arithmetic expression locally without calling an LLM.

**Supported syntax:**
- Integers and decimal literals: `42`, `3.14`
- Operators: `+`, `-`, `*`, `/`, `%`, `**`
- Parentheses: `(2 + 3) * 4`
- Unary minus/plus: `-5`, `+3`

**Resource limits (integer exponentiation only):**
- Base: `abs(base) ≤ 1,000,000`
- Exponent: `abs(exponent) ≤ 1,000`
- Float exponentiation is bounded by IEEE 754 and is not restricted
- Negative exponents (e.g. `2 ** -1 = 0.5`) are allowed

**Rejected inputs (REFUSED):**
- Any AST node other than `Expression`, `Constant` (numeric), `BinOp`,
  `UnaryOp` — this blocks `Call`, `Name`, `Attribute`, `Import`, etc.
- Integer exponentiation operands exceeding the limits above
- Expressions longer than 200 characters
- Syntax errors

**Rejected inputs (ERROR):**
- Empty or non-string input
- Division or modulo by zero
- Non-finite float results (overflow)

**Security:** `eval()` and `exec()` are never called.  The expression is
parsed with `ast.parse(mode="eval")` and the tree is walked manually
against an explicit allowlist.

---

## 6. File search (`actions/file_search.py`)

### `file_search(query, root=None) -> ExecutionResult`

Searches for files whose names contain `query` (case-insensitive) within
a restricted directory.

**Arguments:**
- `query` — partial or full filename (required, non-empty string)
- `root` — directory to search (optional; defaults to `FILE_SEARCH_ROOT`)

**Boundary enforcement:**
- Default root: `core.config.FILE_SEARCH_ROOT` (user home directory)
- Any supplied `root` must resolve (via `os.path.realpath`) to a path
  inside `FILE_SEARCH_ROOT`
- The traversal guard runs **before** the existence check — a
  non-existent path outside the boundary returns `REFUSED`, not `ERROR`
- Every matched path is also resolved and checked before being returned

**Limits:**
- Maximum results: `FILE_SEARCH_MAX_RESULTS` (50)
- Maximum traversal depth: `FILE_SEARCH_MAX_DEPTH` (10)

**Return values:**
- `SUCCESS` with non-empty list — matches found
- `SUCCESS` with empty list — no matches (informative message in `error`)
- `REFUSED` — root resolves outside the permitted boundary
- `ERROR` — empty query, missing directory, or permission failure

**Security:** File contents are never read.  Only filenames from
`os.walk` are examined.

---

## 7. Running the tests

```
# Full suite
python -m pytest tests/ -v

# Individual files
python -m pytest tests/test_actions.py -q
python -m pytest tests/test_router.py -q
python -m pytest tests/test_end_to_end.py -q
python -m pytest tests/test_safety.py -q
```

No API keys, network access, or real application launches are required.
File-search tests use temporary directories.  Application and browser
tests use mocks.

---

## 8. Known Windows-specific limitations

- `calc.exe` on Windows 10/11 is a UWP app; `System32\calc.exe` is a
  stub that launches the Store app.  The launcher returns `SUCCESS` when
  the stub starts, but the visible window is the UWP Calculator.
- `SnippingTool.exe` may not exist on all Windows editions.
- `wordpad.exe` was removed from Windows 11 24H2; the launcher returns
  `ERROR` with a clear message when the executable is missing.
- `webbrowser.open` delegates browser selection to the OS default browser
  setting; the specific browser cannot be controlled from this layer.
- File-search uses `os.walk` which does not follow Windows junctions by
  default; junction targets outside the root are not traversed.

---

## 9. Integration with Person 1's router

The router produces a `RoutingDecision`.  For `Route.LOCAL` decisions,
the caller passes `decision.action_name` and `decision.validated_args`
directly to `execute()`:

```python
from actions.registry import execute
from router.task_router import route
from core.schemas import TaskRequest

decision = route(TaskRequest(raw_input="calculate 10 + 5"))
if decision.route.value == "LOCAL":
    result = execute(decision.action_name, decision.validated_args)
```

`Route.LLM` and `Route.NONE` decisions are not passed to the registry.
