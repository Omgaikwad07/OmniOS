"""
actions/open_file.py
====================
Safe local file opener for OmniOS.

Opens a file with its default Windows application using ``os.startfile``.
No ``shell=True`` is used.  Only files inside the configured root
directory and with an allowlisted extension may be opened.

Safety properties
-----------------
* Only allowlisted file extensions are accepted.
* The resolved path must sit inside ``FILE_OPEN_ROOT`` (same boundary
  as file search — the user's home directory by default).
* Path traversal via ``..`` or absolute paths outside the root is
  blocked via ``os.path.realpath`` containment check.
* If the caller supplies only a filename (no directory), the action
  searches for it inside the root and opens the first match.
* File contents are never read by this module.
"""

from __future__ import annotations

import os
from typing import Optional

import core.config as _cfg
from core.schemas import ExecutionResult, ResultStatus


def open_file(
    filename: str,
    root: Optional[str] = None,
) -> ExecutionResult:
    """Open a file with its default Windows application.

    Parameters
    ----------
    filename : str
        A filename (e.g. ``report.pdf``) or a path relative to *root*.
        Absolute paths are accepted only when they resolve inside the
        permitted root.
    root : str | None
        Directory boundary.  Defaults to ``FILE_SEARCH_ROOT``.

    Returns
    -------
    ExecutionResult
        SUCCESS when the file is opened; REFUSED for policy violations;
        ERROR when the file is missing or the OS call fails.
    """
    if not filename or not isinstance(filename, str):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="filename must be a non-empty string.",
        )

    filename = filename.strip()
    if not filename:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="filename must not be blank.",
        )

    # --- Extension check ---
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower not in _cfg.FILE_OPEN_ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(_cfg.FILE_OPEN_ALLOWED_EXTENSIONS))
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=(
                f"File extension '{ext_lower or '(none)'}' is not allowed. "
                f"Supported extensions: {allowed}."
            ),
        )

    # --- Resolve root boundary ---
    allowed_root = os.path.realpath(_cfg.FILE_SEARCH_ROOT)
    search_root = os.path.realpath(root if root else _cfg.FILE_SEARCH_ROOT)

    # Traversal guard on supplied root.
    if root is not None:
        if search_root != allowed_root and not search_root.startswith(allowed_root + os.sep):
            return ExecutionResult(
                status=ResultStatus.REFUSED,
                error=(
                    f"Root '{root}' resolves outside the permitted "
                    f"boundary '{allowed_root}'."
                ),
            )

    # --- Resolve the target path ---
    # If filename looks like an absolute path, resolve it directly.
    # Otherwise treat it as relative to search_root, or search for it.
    if os.path.isabs(filename):
        candidate = os.path.realpath(filename)
    else:
        # Try as a direct relative path first.
        direct = os.path.realpath(os.path.join(search_root, filename))
        if os.path.isfile(direct):
            candidate = direct
        else:
            # Fall back: search for the filename inside the root.
            candidate = _find_file(filename, search_root)
            if candidate is None:
                return ExecutionResult(
                    status=ResultStatus.ERROR,
                    error=f"File '{filename}' not found in '{search_root}'.",
                )

    # --- Containment check on the resolved target ---
    if candidate != allowed_root and not candidate.startswith(allowed_root + os.sep):
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=(
                f"File '{filename}' resolves outside the permitted "
                f"boundary '{allowed_root}'."
            ),
        )

    # --- Existence check ---
    if not os.path.isfile(candidate):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"File not found: '{candidate}'.",
        )

    # --- Open with default application ---
    try:
        os.startfile(candidate)  # Windows only; no shell=True
        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            output=f"Opened '{candidate}'.",
        )
    except OSError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Failed to open '{candidate}': {exc}",
        )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _find_file(filename: str, root: str) -> Optional[str]:
    """Return the realpath of the first file matching *filename* under *root*.

    Case-insensitive on Windows.  Depth-limited to FILE_SEARCH_MAX_DEPTH.
    Returns ``None`` when nothing is found.
    """
    name_lower = filename.lower()
    allowed_root = os.path.realpath(_cfg.FILE_SEARCH_ROOT)

    for current_root, dirs, files in os.walk(root, topdown=True, onerror=None):
        depth = current_root[len(root):].count(os.sep)
        if depth >= _cfg.FILE_SEARCH_MAX_DEPTH:
            dirs.clear()
            continue
        for fname in files:
            if fname.lower() == name_lower:
                resolved = os.path.realpath(os.path.join(current_root, fname))
                # Containment check on each candidate.
                if resolved == allowed_root or resolved.startswith(allowed_root + os.sep):
                    return resolved
    return None
