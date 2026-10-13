"""
actions/file_search.py
======================
Restricted filename search for OmniOS.

Searches only within a configured root directory (default: the current
user's home folder).  File contents are never read — only filenames and
their paths are examined.

Safety properties
-----------------
* The search root is resolved with ``os.path.realpath`` before use so
  symlinks cannot be used to escape the allowed tree.
* Every matched path is also resolved and checked to confirm it still
  sits inside the root — path-traversal attempts are rejected.
* Whole-drive searching is never performed; there is no way to pass
  a root of ``C:\\`` through the public API without an explicit override.
* Hard limits on traversal depth and result count prevent runaway scans.
"""

from __future__ import annotations

import os
from typing import Optional

import core.config as _cfg
from core.schemas import ExecutionResult, ResultStatus


def file_search(
    query: str,
    root: Optional[str] = None,
) -> ExecutionResult:
    """Search for files whose names contain *query* inside *root*.

    Parameters
    ----------
    query : str
        Partial or full filename to search for (case-insensitive).
    root : str | None
        Directory to search within.  Defaults to ``FILE_SEARCH_ROOT``
        (the user's home directory).  Must resolve to a path that is
        itself inside ``FILE_SEARCH_ROOT`` — callers cannot escape the
        configured boundary by supplying an absolute path outside it,
        unless ``FILE_SEARCH_ROOT`` is explicitly overridden in config.

    Returns
    -------
    ExecutionResult
        SUCCESS with a list of matching paths in ``output`` (empty list
        when nothing matches); ERROR for missing/inaccessible root or
        bad arguments; REFUSED for path-traversal attempts.
    """
    # --- Input validation ---
    if not query or not isinstance(query, str):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="query must be a non-empty string.",
        )

    query = query.strip()
    if not query:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="query must not be blank.",
        )

    # --- Resolve search root ---
    # Read config at call time so tests can patch core.config attributes.
    search_root = os.path.realpath(root if root else _cfg.FILE_SEARCH_ROOT)
    allowed_root = os.path.realpath(_cfg.FILE_SEARCH_ROOT)

    # Traversal guard FIRST — before any existence check so that a path
    # that escapes the boundary but does not exist still returns REFUSED,
    # not ERROR (which would leak information about the boundary).
    if root is not None:
        if not search_root.startswith(allowed_root + os.sep) and search_root != allowed_root:
            return ExecutionResult(
                status=ResultStatus.REFUSED,
                error=(
                    f"Search root '{root}' resolves outside the permitted "
                    f"boundary '{allowed_root}'."
                ),
            )

    if not os.path.exists(search_root):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Search directory does not exist: '{search_root}'.",
        )

    if not os.path.isdir(search_root):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Search path is not a directory: '{search_root}'.",
        )

    # --- Walk and match ---
    query_lower = query.lower()
    matches: list[str] = []

    try:
        for current_root, dirs, files in os.walk(search_root, topdown=True, onerror=None):
            # Depth check: count separators relative to search_root.
            depth = current_root[len(search_root):].count(os.sep)
            if depth >= _cfg.FILE_SEARCH_MAX_DEPTH:
                dirs.clear()  # prune — do not descend further
                continue

            for filename in files:
                if query_lower in filename.lower():
                    full_path = os.path.realpath(os.path.join(current_root, filename))

                    # Path-traversal guard: resolved path must stay inside root.
                    if not full_path.startswith(search_root + os.sep) and full_path != search_root:
                        continue

                    matches.append(full_path)
                    if len(matches) >= _cfg.FILE_SEARCH_MAX_RESULTS:
                        break

            if len(matches) >= _cfg.FILE_SEARCH_MAX_RESULTS:
                break

    except PermissionError as exc:
        # Root itself is inaccessible.
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Permission denied accessing '{search_root}': {exc}",
        )

    if not matches:
        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            output=[],
            error=f"No files matching '{query}' found in '{search_root}'.",
        )

    return ExecutionResult(
        status=ResultStatus.SUCCESS,
        output=matches,
    )
