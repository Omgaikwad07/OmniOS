"""
actions/urls.py
===============
URL opener for OmniOS.

Only HTTP and HTTPS URLs are accepted.  Dangerous schemes such as
``file:``, ``javascript:``, and ``data:`` are explicitly rejected.
Opening is delegated to ``webbrowser.open`` — the correct stdlib API
for launching the system default browser on Windows without invoking
an arbitrary shell command.
"""

from __future__ import annotations

import webbrowser
from urllib.parse import urlparse

from core.schemas import ExecutionResult, ResultStatus

# Schemes that are safe to open in a browser.
_ALLOWED_SCHEMES = {"http", "https"}

# Schemes that must never be executed, listed explicitly for clarity.
_BLOCKED_SCHEMES = {"file", "javascript", "data", "ftp", "ftps", "mailto", "vbscript"}


def open_url(url: str) -> ExecutionResult:
    """Open a URL in the system default browser.

    Parameters
    ----------
    url : str
        A fully-qualified HTTP or HTTPS URL.

    Returns
    -------
    ExecutionResult
        SUCCESS when the browser is invoked; REFUSED for disallowed
        schemes or malformed input; ERROR on launch failure.
    """
    if not url or not isinstance(url, str):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="url must be a non-empty string.",
        )

    url = url.strip()

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"Malformed URL: {exc}",
        )

    scheme = parsed.scheme.lower()

    # Reject explicitly blocked schemes first.
    if scheme in _BLOCKED_SCHEMES:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"Scheme '{scheme}:' is not allowed for security reasons.",
        )

    # Reject anything that is not http/https (includes empty scheme).
    if scheme not in _ALLOWED_SCHEMES:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"Only http and https URLs are supported. Got: '{url}'.",
        )

    # Require a non-empty host (rejects bare "https://" etc.).
    if not parsed.netloc:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"URL has no host: '{url}'.",
        )

    try:
        opened = webbrowser.open(url)
        if not opened:
            return ExecutionResult(
                status=ResultStatus.ERROR,
                error=f"webbrowser.open reported failure for '{url}'.",
            )
        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            output=f"Opened {url} in the default browser.",
        )
    except OSError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Failed to open '{url}': {exc}",
        )
