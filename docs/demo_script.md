# OmniOS Demo Script

A short, reproducible demonstration sequence for presenting OmniOS to the
team or mentor. Each step shows the command, the expected output, and whether
the feature is fully implemented or a placeholder.

---

## Setup (before the demo)

```
cd OmniOS
.venv\Scripts\activate      # or: python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

---

## Step 1 — Calculator (implemented)

**Command:**
```
OmniOS> calculate 10 + 5 * 2
```

**Expected output:**
```
  Intent   : CALCULATE
  Route    : LOCAL
  Status   : SUCCESS
  Output   : 20
  Used LLM : False
```

**What to say:** "The router classifies this as a CALCULATE intent and routes
it locally. The calculator uses Python's AST module — no `eval()` is called.
Operator precedence is respected: multiplication before addition gives 20."

---

## Step 2 — Calculator safety (implemented)

**Command:**
```
OmniOS> calculate __import__('os')
```

**Expected output:**
```
  Status   : REFUSED
  Error    : Unsupported expression node 'Call'. Only arithmetic expressions are allowed.
```

**What to say:** "Injection attempts are blocked at the AST level before any
computation. The expression is never passed to `eval()`."

---

## Step 3 — Open an application (implemented)

**Command:**
```
OmniOS> open notepad
```

**Expected output:**
```
  Intent   : OPEN_APP
  Route    : LOCAL
  Status   : SUCCESS
  Output   : Launched notepad.
  Used LLM : False
```

**What to say:** "Only allowlisted applications can be launched. The registry
maps the name to an absolute executable path and calls `subprocess.Popen`
with no `shell=True`."

---

## Step 4 — Application allowlist enforcement (implemented)

**Command:**
```
OmniOS> open chrome
```

**Expected output:**
```
  Status   : REFUSED
  Error    : 'chrome' is not an approved application. Supported apps: calculator, cmd, ...
```

**What to say:** "Anything not on the allowlist is refused before any process
is created. Arbitrary executable paths and shell injection strings are also
rejected."

---

## Step 5 — Open a URL (implemented)

**Command:**
```
OmniOS> open https://python.org
```

**Expected output:**
```
  Intent   : OPEN_URL
  Route    : LOCAL
  Status   : SUCCESS
  Output   : Opened https://python.org in the default browser.
  Used LLM : False
```

**What to say:** "The URL opener accepts only `http` and `https`. It uses
`webbrowser.open` — no shell command is constructed."

---

## Step 6 — URL scheme blocking (implemented)

**Command:**
```
OmniOS> open file:///C:/Windows/win.ini
```

**Expected output:**
```
  Status   : REFUSED
  Error    : Scheme 'file:' is not allowed for security reasons.
```

**What to say:** "Seven dangerous schemes are explicitly blocked: `file`,
`javascript`, `data`, `ftp`, `ftps`, `mailto`, and `vbscript`."

---

## Step 7 — File search (implemented)

**Command:**
```
OmniOS> find notes.txt on my computer
```

**Expected output (if the file exists in your home directory):**
```
  Intent   : FILE_SEARCH
  Route    : LOCAL
  Status   : SUCCESS
  Output   : ['C:\Users\<you>\Documents\notes.txt']
  Used LLM : False
```

**Expected output (if the file does not exist):**
```
  Status   : SUCCESS
  Output   : []
  Error    : No files matching 'notes.txt' found in 'C:\Users\<you>'.
```

**What to say:** "File search is restricted to the user's home directory.
Path traversal attempts are blocked before any directory walk begins."

---

## Step 8 — LLM task routing (router implemented; LLM not implemented)

**Command:**
```
OmniOS> summarize my meeting notes
```

**Expected output:**
```
  Intent   : LLM_TASK
  Route    : LLM
  Confidence: 90%
  Result   : LLM integration not yet implemented.
             (No API key configured; no call was made.)
```

**What to say:** "The classifier correctly identifies this as an LLM task and
routes it to the LLM layer. The LLM integration itself is not yet implemented —
no API call is made and no credentials are required to run the demo."

---

## Step 9 — Unknown command (implemented)

**Command:**
```
OmniOS> do something weird
```

**Expected output:**
```
  Intent   : UNKNOWN
  Route    : NONE
  Result   : Could not determine a supported action.
             Try: calculate, open <app>, open <url>,
             or: find <filename>
```

**What to say:** "Unrecognised commands are handled gracefully. The system
never guesses a shell command or executes arbitrary input."

---

## Step 10 — Exit (implemented)

**Command:**
```
OmniOS> exit
```

**Expected output:**
```
Goodbye.
```

---

## Running the test suite

```
python -m pytest tests/ -q
```

Expected: `199 passed` (all deterministic, no network, no real launches).

---

## What is not yet implemented

| Feature | Status |
|---|---|
| LLM integration | Stub — no API call is made |
| Voice interface | Not started |
| GUI | Not started |
| Context/memory system | Stub only |
| PDF summariser | Stub only |
