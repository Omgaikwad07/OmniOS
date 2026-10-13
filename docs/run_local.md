# Running OmniOS Locally

Step-by-step guide to setting up and running the OmniOS CLI demo on Windows.

---

## 1. Prerequisites

- Windows 10 or Windows 11
- Python 3.10 or later — verify with `python --version`
- `pip` — verify with `pip --version`

---

## 2. Setup

```
git clone <repository-url>
cd OmniOS
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3. Launch

```
python app.py
```

---

## 4. Expected console session

```
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

OmniOS> calculate 10 + 5 * 2
────────────────────────────────────────────
  Intent   : CALCULATE
  Route    : LOCAL
  Confidence: 85%
  Status   : SUCCESS
  Output   : 20
  Used LLM : False
────────────────────────────────────────────

OmniOS> open notepad
────────────────────────────────────────────
  Intent   : OPEN_APP
  Route    : LOCAL
  Confidence: 90%
  Status   : SUCCESS
  Output   : Launched notepad.
  Used LLM : False
────────────────────────────────────────────

OmniOS> open https://example.com
────────────────────────────────────────────
  Intent   : OPEN_URL
  Route    : LOCAL
  Confidence: 95%
  Status   : SUCCESS
  Output   : Opened https://example.com in the default browser.
  Used LLM : False
────────────────────────────────────────────

OmniOS> find report.pdf on my computer
────────────────────────────────────────────
  Intent   : FILE_SEARCH
  Route    : LOCAL
  Confidence: 85%
  Status   : SUCCESS
  Output   : ['C:\Users\<you>\Documents\report.pdf']
  Used LLM : False
────────────────────────────────────────────

OmniOS> summarize my meeting notes
────────────────────────────────────────────
  Intent   : LLM_TASK
  Route    : LLM
  Confidence: 90%
  Result   : LLM integration not yet implemented.
             (No API key configured; no call was made.)
────────────────────────────────────────────

OmniOS> exit
Goodbye.
```

---

## 5. Configuration

| Setting | Default | Location |
|---|---|---|
| File search root | `%USERPROFILE%` (home directory) | `core/config.py` |
| Max search results | 50 | `core/config.py` |
| Max search depth | 10 subdirectory levels | `core/config.py` |
| App allowlist | 9 Windows apps | `core/config.py` |

No environment variables or API keys are required to run local actions.

The `.env.example` file is a placeholder for future LLM configuration.

---

## 6. Limitations

- File search is restricted to the user's home directory. It will not
  search `C:\Windows`, `C:\Program Files`, or any path outside `%USERPROFILE%`.
- Only allowlisted applications can be launched. Arbitrary executable
  paths are rejected.
- Only `http` and `https` URLs are accepted. `file:`, `javascript:`,
  `data:`, `ftp:`, `mailto:`, and `vbscript:` are blocked.
- The calculator accepts arithmetic only. Function calls, variable names,
  and imports are rejected.
- LLM tasks are classified and routed correctly but not executed — the
  LLM integration layer is not yet implemented.

---

## 7. Safe manual testing

The following commands are safe to run interactively:

```
calculate 2 ** 10
calculate (100 - 32) / 1.8
open notepad
open https://python.org
find .py on my computer
```

The following will be refused (by design — safe to try):

```
open C:\malware\evil.exe
open file:///C:/Windows/win.ini
open javascript:alert(1)
calculate __import__('os')
find ../../../Windows/System32
```

---

## 8. Running tests

```
python -m pytest tests/ -q
```

All tests are deterministic. No applications are launched, no browser
windows are opened, and no network calls are made during the test suite.
