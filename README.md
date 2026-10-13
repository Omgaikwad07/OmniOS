# OmniOS

OmniOS is a Windows desktop assistant that accepts natural-language commands,
classifies them locally, and executes supported actions — calculations, file
searches, application launches, and URL opening — without sending anything to
an LLM unless the task genuinely requires language reasoning.

---

## Current implementation status

| Feature | Status |
|---|---|
| Intent classifier (rule-based, no LLM) | Implemented |
| Task router | Implemented |
| Calculator (AST-based, no `eval`) | Implemented |
| File search (home-directory scoped) | Implemented |
| Application launcher (allowlist only) | Implemented |
| URL opener (http/https only) | Implemented |
| Action registry | Implemented |
| CLI demo (`app.py`) | Implemented |
| LLM integration | Stub only — not implemented |
| Voice interface | Not implemented |
| GUI | Not implemented |
| Context/memory system | Stub only — not implemented |

---

## Prerequisites

- Windows 10 or Windows 11
- Python 3.10 or later ([python.org](https://www.python.org/downloads/))
- `pip` (included with Python)

---

## Setup

### 1. Clone the repository

```
git clone <repository-url>
cd OmniOS
```

### 2. Create and activate a virtual environment

```
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

## Launch the demo

```
python app.py
```

You will see a prompt:

```
OmniOS>
```

---

## Example commands

### Calculation

```
OmniOS> calculate 10 + 5 * 2
OmniOS> what is (100 - 32) / 1.8
OmniOS> 2 ** 8
```

### File search

```
OmniOS> find report.pdf on my computer
OmniOS> search for notes.txt
OmniOS> locate resume
```

### Open an application

```
OmniOS> open notepad
OmniOS> launch calculator
OmniOS> start paint
```

Allowlisted applications: `calculator`, `notepad`, `paint`, `wordpad`,
`explorer`, `cmd`, `taskmgr`, `task manager`, `snipping tool`.

### Open a URL

```
OmniOS> open https://example.com
OmniOS> open github.com
OmniOS> go to https://docs.python.org
```

Only `http` and `https` URLs are accepted.

### LLM tasks (not yet implemented)

```
OmniOS> summarize my meeting notes
OmniOS> explain what a neural network is
```

These are classified correctly and routed to `LLM`, but the LLM
integration is not yet implemented. The demo will say so clearly.

---

## Exit the demo

```
OmniOS> exit
```

or press `Ctrl+C`.

---

## Run automated tests

```
python -m pytest tests/ -q
```

Expected output: `199 passed` (or more if additional tests have been added).

Do not run `pytest` without the `tests/` path — the repository root
contains `test_router_voice.py` which requires `speech_recognition`
(not installed).

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'core'`**
Run from the repository root (`OmniOS/`), not from a subdirectory.

**`ModuleNotFoundError: No module named 'pytest'`**
Run `pip install -r requirements.txt` (with your virtual environment active).

**`calc.exe` opens but shows the wrong window**
On Windows 10/11, `System32\calc.exe` is a stub that launches the UWP
Calculator app. This is expected behaviour.

**`wordpad` returns ERROR**
WordPad was removed from Windows 11 24H2. The error message will say so.

**`snipping tool` returns ERROR**
SnippingTool.exe may not be present on all Windows editions.

**File search returns no results**
The search is restricted to your home directory (`%USERPROFILE%`).
Ensure the file exists there or in a subdirectory.
