"""
actions/apps.py
===============
Windows application launcher for OmniOS.

Only applications explicitly listed in ``core.config.APP_ALLOWLIST`` can
be launched.  Arbitrary executable paths and shell commands are never
accepted.
"""

from __future__ import annotations

import subprocess

from core.config import APP_ALLOWLIST
from core.schemas import ExecutionResult, ResultStatus


def open_app(app_name: str) -> ExecutionResult:
    """Launch an approved desktop application.

    Parameters
    ----------
    app_name : str
        The name of the application to launch (case-insensitive).
        Must match a key in ``APP_ALLOWLIST``.

    Returns
    -------
    ExecutionResult
        SUCCESS when the process starts; ERROR or REFUSED otherwise.
    """
    if not app_name or not isinstance(app_name, str):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="app_name must be a non-empty string.",
        )

    key = app_name.strip().lower()

    if key not in APP_ALLOWLIST:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"'{app_name}' is not an approved application. "
                  f"Supported apps: {', '.join(sorted(APP_ALLOWLIST))}.",
        )

    exe_path = APP_ALLOWLIST[key]

    try:
        subprocess.Popen([exe_path])  # non-blocking; no shell=True
        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            output=f"Launched {app_name}.",
        )
    except FileNotFoundError:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Executable not found: {exe_path}. "
                  "The application may not be installed on this system.",
        )
    except OSError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Failed to launch '{app_name}': {exc}",
        )
