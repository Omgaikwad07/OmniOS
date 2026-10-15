"""
ui/services.py
==============
Truthful System Status checks.

Nothing here is hard-coded to "Ready": each check inspects the real
configuration or imports the real module.  ``refresh()`` re-reads ``.env`` so
that adding a ``GROQ_API_KEY`` and pressing Refresh genuinely takes effect for
the backend too (``app.process_command`` reads ``core.config.GROQ_API_KEY`` at
call time).
"""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Callable, Optional

READY = "ready"
NOT_CONFIGURED = "not_configured"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ServiceStatus:
    key: str            # local | groq | pdf
    name: str
    state: str          # READY | NOT_CONFIGURED | UNAVAILABLE
    label: str          # text shown next to the dot
    description: str


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def reload_environment() -> None:
    """Re-read ``.env`` and push the key/model into ``core.config``."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    import core.config as cfg
    cfg.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL")
    if model:
        cfg.GROQ_MODEL = model


def check_local_engine() -> ServiceStatus:
    desc = "Command execution, file search, app control, calculations"
    try:
        from actions.registry import execute  # noqa: F401
        from core.schemas import Route, TaskRequest
        from router.task_router import route

        # A real (side-effect free) routing probe, not just an import.
        decision = route(TaskRequest(raw_input="calculate 1 + 1"))
        if decision.route == Route.LOCAL and decision.action_name == "calculate":
            return ServiceStatus("local", "Local Engine", READY, "Ready", desc)
        return ServiceStatus(
            "local", "Local Engine", UNAVAILABLE, "Not Available",
            "Router self-check returned an unexpected decision.",
        )
    except Exception as exc:  # pragma: no cover - depends on install state
        return ServiceStatus(
            "local", "Local Engine", UNAVAILABLE, "Not Available",
            f"{type(exc).__name__}: {exc}"[:90],
        )


def check_groq() -> ServiceStatus:
    import core.config as cfg

    if not getattr(cfg, "GROQ_API_KEY", ""):
        return ServiceStatus(
            "groq", "Groq LLM", NOT_CONFIGURED, "Not Configured",
            "Set GROQ_API_KEY in .env to enable language tasks",
        )
    if not _has_module("groq"):
        return ServiceStatus(
            "groq", "Groq LLM", UNAVAILABLE, "Not Available",
            "API key found, but the 'groq' package is not installed",
        )
    return ServiceStatus(
        "groq", "Groq LLM", READY, "Ready",
        f"API key detected · model {getattr(cfg, 'GROQ_MODEL', '')}",
    )


def check_pdf(groq_ready: bool) -> ServiceStatus:
    if not _has_module("fitz"):
        return ServiceStatus(
            "pdf", "PDF Processing", UNAVAILABLE, "Not Available",
            "PyMuPDF is not installed (pip install PyMuPDF)",
        )
    if groq_ready:
        return ServiceStatus(
            "pdf", "PDF Processing", READY, "Ready",
            "Summarization and document analysis",
        )
    return ServiceStatus(
        "pdf", "PDF Processing", READY, "Ready",
        "Text extraction ready · summaries need Groq",
    )


def refresh(reload_env: bool = True) -> list[ServiceStatus]:
    """Run every check (optionally re-reading ``.env`` first)."""
    if reload_env:
        reload_environment()
    groq = check_groq()
    return [check_local_engine(), groq, check_pdf(groq.state == READY)]
