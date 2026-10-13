
"""Configuration for OmniOS local actions and LLM handling."""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

LLM_TIMEOUT_SECONDS = 30
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_DOCUMENT_CHARS = 60_000
MAX_OUTPUT_TOKENS = 1500

# Application allowlist
_SYSTEM32 = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"), "System32"
)
_SYSWOW64 = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64"
)

APP_ALLOWLIST: dict[str, str] = {
    "calculator": os.path.join(_SYSTEM32, "calc.exe"),
    "notepad": os.path.join(_SYSTEM32, "notepad.exe"),
    "paint": os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
        "Microsoft", "WindowsApps", "mspaint.exe",
    ),
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

# File-search configuration
FILE_SEARCH_ROOT: str = os.path.expanduser("~")
FILE_SEARCH_MAX_RESULTS: int = 50
FILE_SEARCH_MAX_DEPTH: int = 10

# File-open allowlist
FILE_OPEN_ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".doc", ".docx", ".txt", ".csv", ".rtf",
    ".xls", ".xlsx",
    ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mkv",
})
