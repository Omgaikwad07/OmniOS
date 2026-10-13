"""
core/config.py
==============
Static configuration for OmniOS local actions.

All mutable runtime state lives elsewhere; this module contains only
constants so it can be imported without side-effects.
"""

import os

# ---------------------------------------------------------------------------
# Application allowlist
# ---------------------------------------------------------------------------
# Maps the canonical lowercase app name to its absolute Windows executable
# path.  Only apps listed here can be launched by the action layer.
# Paths use environment variables so they work across Windows editions.

_SYSTEM32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
_SYSWOW64 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64")

APP_ALLOWLIST: dict[str, str] = {
    "calculator": os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"), "System32", "calc.exe"
    ),
    "notepad": os.path.join(_SYSTEM32, "notepad.exe"),
    "paint": os.path.join(_SYSTEM32, "mspaint.exe"),
    "wordpad": os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        "Windows NT", "Accessories", "wordpad.exe",
    ),
    "explorer": os.path.join(_SYSTEM32, "explorer.exe"),
    "cmd": os.path.join(_SYSTEM32, "cmd.exe"),
    "taskmgr": os.path.join(_SYSTEM32, "Taskmgr.exe"),
    "task manager": os.path.join(_SYSTEM32, "Taskmgr.exe"),
    "snipping tool": os.path.join(_SYSTEM32, "SnippingTool.exe"),
}

# ---------------------------------------------------------------------------
# File-search defaults
# ---------------------------------------------------------------------------

# Default root directory for file searches.  Never search the whole drive.
FILE_SEARCH_ROOT: str = os.path.expanduser("~")

# Hard limits to prevent runaway traversal.
FILE_SEARCH_MAX_RESULTS: int = 50
FILE_SEARCH_MAX_DEPTH: int = 10
