"""
router/task_router.py
=====================
Converts a ``ClassificationResult`` into a ``RoutingDecision``.

This module is the single source of truth for *where* a task runs.
It does **not** execute anything — it only decides the route and
prepares the arguments so that downstream action handlers or the
LLM agent layer can take over.

Public API
----------
    route(task: TaskRequest) -> RoutingDecision

Design decisions
----------------
* **LOCAL for deterministic actions** – OPEN_APP, OPEN_URL, CALCULATE,
  and FILE_SEARCH are all handled on the local machine.
* **LLM for reasoning tasks** – summarisation, explanation, creative
  writing, etc.
* **NONE for UNKNOWN** – the router never guesses a shell command or
  ``eval``s user input.
* **Action-name mapping** – each LOCAL intent is mapped to a named
  action string that the action registry (Member 2) will resolve.
* **Argument extraction** – basic argument parsing is done here so
  that action handlers receive validated_args rather than raw text.
  Parsing is intentionally shallow; handlers should do their own
  deep validation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from core.schemas import (
    Intent,
    Route,
    RoutingDecision,
    TaskRequest,
)
from router.classifier import ClassificationResult, classify


# ---------------------------------------------------------------------------
# Intent → (Route, action_name) mapping
# ---------------------------------------------------------------------------

_INTENT_ROUTE_MAP: Dict[Intent, tuple] = {
    Intent.OPEN_APP:    (Route.LOCAL, "open_app"),
    Intent.OPEN_URL:    (Route.LOCAL, "open_url"),
    Intent.CALCULATE:   (Route.LOCAL, "calculate"),
    Intent.FILE_SEARCH: (Route.LOCAL, "file_search"),
    Intent.LLM_TASK:    (Route.LLM,  None),
    Intent.UNKNOWN:     (Route.NONE, None),
}


# ---------------------------------------------------------------------------
# Lightweight argument extractors (per-intent)
# ---------------------------------------------------------------------------

def _extract_open_app_args(text: str) -> Dict[str, Any]:
    """Try to extract the application name from the request."""
    # Matches "open <app>", "launch <app>", etc.
    match = re.search(
        r"\b(?:open|launch|start|run)\s+(.+)",
        text, re.IGNORECASE,
    )
    if match:
        app_name = match.group(1).strip().rstrip(".")
        return {"app_name": app_name}
    return {"app_name": text}


def _extract_open_url_args(text: str) -> Dict[str, Any]:
    """Try to extract a URL from the request."""
    # First, look for an explicit http(s) URL.
    url_match = re.search(r"(https?://\S+)", text, re.IGNORECASE)
    if url_match:
        return {"url": url_match.group(1)}
    # Fallback: look for a domain-like token (e.g. "google.com").
    domain_match = re.search(
        r"\b(?:open|go\s+to|visit|navigate\s+to|browse)\s+(\S+\.\S+)",
        text, re.IGNORECASE,
    )
    if domain_match:
        raw = domain_match.group(1).rstrip(".")
        url = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"
        return {"url": url}
    # Fallback: look for a named website (e.g. "open Google website").
    site_match = re.search(
        r"\b(?:open|go\s+to|visit|navigate\s+to|browse)\s+(?:the\s+)?(\S+)\s+(?:website|site|webpage)\b",
        text, re.IGNORECASE,
    )
    if site_match:
        target = site_match.group(1).rstrip(".")
        if "." not in target:
            target = f"https://www.{target.lower()}.com"
        elif not target.startswith(("http://", "https://")):
            target = f"https://{target}"
        return {"url": target}
    return {"url": text}


def _extract_calculate_args(text: str) -> Dict[str, Any]:
    """Try to extract and normalize a math expression from the request."""
    # Strip leading verbs.
    cleaned = re.sub(
        r"^(?:what\s+is|calculate|compute|evaluate|solve|perform)\s+",
        "", text, flags=re.IGNORECASE,
    ).strip()

    # Convert spoken math operators to standard symbols.
    cleaned = re.sub(r"\btimes\b", "*", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmultiplied\s+by\b", "*", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bplus\b", "+", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bminus\b", "-", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdivided\s+by\b", "/", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdivide\s+by\b", "/", cleaned, flags=re.IGNORECASE)

    # Convert spoken 'into' to '*' only when clearly occurring between mathematical operands
    # (e.g. between numbers, parentheses)
    cleaned = re.sub(r"(?<=\d|\))\s*\binto\b\s*(?=\d|\()", " * ", cleaned, flags=re.IGNORECASE)

    # Normalize 'x' or 'X' multiplication where unambiguous.
    cleaned = re.sub(r"(?<=\d|\))\s*[xX]\s*(?=\d|\()", " * ", cleaned)
    cleaned = re.sub(r"\s+[xX]\s+", " * ", cleaned)

    # Keep only digits, operators, parens, whitespace, decimal points.
    expression = re.sub(r"[^\d\s\+\-\*/\(\)\.%\^]", "", cleaned).strip()
    expression = re.sub(r"\s+", " ", expression).strip()
    return {"expression": expression if expression else cleaned}


def _extract_file_search_args(text: str) -> Dict[str, Any]:
    """Try to extract a search query and optional location from the request."""
    # Check for a location phrase
    location = None
    loc_match = re.search(
        r"\b(?:on|in|from|under|search|look\s+in|check)\s+(?:my\s+|the\s+)?(gallery\s+documents|gallery|pictures|photos|desktop|computer|files|system|disk|drive|downloads|documents|pc|laptop)\b",
        text, re.IGNORECASE,
    )
    if loc_match:
        loc_val = loc_match.group(1).lower()
        if loc_val not in ("computer", "files", "system", "disk", "drive", "pc", "laptop"):
            location = loc_val

    # Try to grab a quoted filename first.
    quoted = re.search(r'["\'](.+?)["\']', text)
    if quoted:
        result: Dict[str, Any] = {"query": quoted.group(1)}
        if location:
            result["location"] = location
        return result

    # Strip trailing location phrases
    cleaned = re.sub(
        r"\s+(?:on|in|from|under)\s+(?:my\s+|the\s+)?(?:gallery|pictures|photos|desktop|downloads|documents|computer|pc|laptop|files|system|disk|drive|folder|directory)(?:\s+(?:documents|folder|directory|files|gallery|drive))?\s*$",
        "", text, flags=re.IGNORECASE,
    ).strip()

    # Strip leading command verbs with location (e.g. 'search desktop for notes.txt')
    cleaned = re.sub(
        r"^(?:find|search|locate|look(?:\s+in)?|where\s+is|open|view|show)\s+(?:(?:on|in|from|under)\s+)?(?:(?:my|the|a)\s+)?(?:desktop|computer|files|system|disk|drive|downloads|documents|gallery|pc|laptop)\s+(?:for\s+)?",
        "", cleaned, flags=re.IGNORECASE,
    ).strip()

    # Strip leading command verbs and prepositions
    cleaned = re.sub(
        r"^(?:find|search(?:\s+for)?|locate|look\s+for|where\s+is|open|view|show)\s+",
        "", cleaned, flags=re.IGNORECASE,
    ).strip()

    # If a naming phrase is present (e.g. 'my photo named Om JPG', 'file called report.pdf')
    named_cleaned = re.sub(
        r"^(?:(?:my|the|a)\s+)?(?:photo|picture|image|video|file|folder|document|doc)?\s*(?:named|called|with\s+(?:the\s+)?name)\s+",
        "", cleaned, flags=re.IGNORECASE,
    ).strip()
    if named_cleaned and named_cleaned != cleaned:
        cleaned = named_cleaned
    else:
        # Strip filler words (e.g. "the file", "my", "the", "a")
        cleaned = re.sub(
            r"^(?:the\s+file|a\s+file|file|the\s+folder|folder|the\s+document|document)\s+",
            "", cleaned, flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(r"^(?:my|the|a)\s+", "", cleaned, flags=re.IGNORECASE).strip()

    # Clean any trailing location phrase that might remain after extracting named query
    cleaned = re.sub(
        r"\s+(?:on|in|from|under)\s+(?:my\s+|the\s+)?(?:gallery|pictures|photos|desktop|downloads|documents|computer|pc|laptop|files|system|disk|drive|folder|directory)(?:\s+(?:documents|folder|directory|files|gallery|drive))?\s*$",
        "", cleaned, flags=re.IGNORECASE,
    ).strip()

    result = {"query": cleaned if cleaned else text}
    if location:
        result["location"] = location
    return result


_ARG_EXTRACTORS = {
    Intent.OPEN_APP:    _extract_open_app_args,
    Intent.OPEN_URL:    _extract_open_url_args,
    Intent.CALCULATE:   _extract_calculate_args,
    Intent.FILE_SEARCH: _extract_file_search_args,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def route(task: TaskRequest) -> RoutingDecision:
    """Classify a user request and produce a routing decision.

    Parameters
    ----------
    task : TaskRequest
        The incoming user request.

    Returns
    -------
    RoutingDecision
        Contains the intent, route, confidence, a human-readable
        explanation, the target action name, and any validated
        arguments extracted from the input.

    Notes
    -----
    * This function never executes a Windows action or makes an LLM
      API call — it only *decides* the route.
    * ``eval()`` and arbitrary shell commands are never used.
    """
    classification: ClassificationResult = classify(task.raw_input)

    intent = classification.intent
    route_enum, action_name = _INTENT_ROUTE_MAP.get(
        intent, (Route.NONE, None),
    )

    # Build a human-readable explanation.
    if intent == Intent.UNKNOWN:
        explanation = (
            "Could not determine a clear intent from the request. "
            "No action will be taken."
        )
    elif route_enum == Route.LLM:
        explanation = (
            f"Classified as {intent.value} (confidence "
            f"{classification.confidence:.0%}). Routing to LLM for "
            f"language reasoning."
        )
    else:
        explanation = (
            f"Classified as {intent.value} (confidence "
            f"{classification.confidence:.0%}). Routing to local "
            f"action '{action_name}'."
        )

    # Extract arguments for LOCAL actions.
    validated_args: Optional[Dict[str, Any]] = None
    if route_enum == Route.LOCAL and intent in _ARG_EXTRACTORS:
        validated_args = _ARG_EXTRACTORS[intent](task.raw_input)

    return RoutingDecision(
        intent=intent,
        route=route_enum,
        confidence=classification.confidence,
        explanation=explanation,
        action_name=action_name,
        validated_args=validated_args,
    )
