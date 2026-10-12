"""
router/classifier.py
====================
Lightweight, rule-based intent classifier for OmniOS.

This module maps raw natural-language requests to one of the supported
`Intent` values using keyword and pattern matching — **no LLM call is
made**.  The design is intentionally simple so it can be replaced or
supplemented with a model-based classifier later without changing the
public interface.

Public API
----------
    classify(user_input: str) -> ClassificationResult

Design decisions
----------------
* **Deterministic** – relies on compiled regexes and keyword sets, so
  results are reproducible and testable without network access.
* **Confidence scoring** – a match on a strong pattern (regex) gets
  0.90, a keyword-only match gets 0.70, and UNKNOWN gets 0.30 so
  downstream consumers can threshold on confidence.
* **Ambiguity handling** – when multiple intents match, the one with
  the highest confidence wins.  Ties are broken by preferring LOCAL
  intents over LLM (safer default).  If nothing matches, UNKNOWN is
  returned rather than guessing.
* **No side-effects** – classify() is a pure function.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from core.schemas import Intent


# ---------------------------------------------------------------------------
# Classification result (internal to the router layer)
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    """Result produced by the classifier.

    Attributes
    ----------
    intent : Intent
        The most likely intent for the user's input.
    confidence : float
        A 0.0–1.0 score.  ≥ 0.70 → strong match, < 0.50 → uncertain.
    matched_keywords : list[str]
        Which keywords or patterns triggered the match (useful for
        debugging and for the router's ``explanation`` field).
    """

    intent: Intent
    confidence: float
    matched_keywords: List[str]


# ---------------------------------------------------------------------------
# Pattern / keyword tables
# ---------------------------------------------------------------------------

# Each entry is (Intent, confidence_boost, compiled_regex).
# Patterns are checked first; they are more specific than bare keywords.
_PATTERNS: List[Tuple[Intent, float, re.Pattern]] = [
    # OPEN_URL – explicit URLs, domains, or website references
    (Intent.OPEN_URL, 0.95, re.compile(
        r"\bhttps?://\S+", re.IGNORECASE)),
    (Intent.OPEN_URL, 0.95, re.compile(
        r"\b(?:open|go\s+to|visit|navigate\s+to|browse)\s+\S+\.\S+",
        re.IGNORECASE)),
    (Intent.OPEN_URL, 0.95, re.compile(
        r"\b(?:open|go\s+to|visit|navigate\s+to|browse)\s+.*?\b(?:website|site|webpage|url)\b",
        re.IGNORECASE)),

    # OPEN_APP – "open <app>", "launch <app>", "start <app>", "run <app>"
    (Intent.OPEN_APP, 0.90, re.compile(
        r"\b(?:open|launch|start|run)\s+(?!https?://|(?:my|the\s+file|a\s+file)\b)(?!\S+\s+(?:website|site|webpage)\b)(?!.*?\b(?:photo|picture|image|resume)\b)\S+",
        re.IGNORECASE)),

    # CALCULATE – expression-like: digits, operators, 'x', and spoken math words (including 'into')
    (Intent.CALCULATE, 0.90, re.compile(
        r"\b(?:what\s+is|calculate|compute|evaluate|solve|perform)\s+"
        r"[\d\s\+\-\*/\(\)\.%\^xX]+$",
        re.IGNORECASE)),
    (Intent.CALCULATE, 0.90, re.compile(
        r"\b(?:what\s+is|calculate|compute|evaluate|solve|perform)\s+"
        r"(?:[\d\s\+\-\*/\(\)\.%\^xX]|plus|minus|times|into|divided\s+by)+$",
        re.IGNORECASE)),
    (Intent.CALCULATE, 0.85, re.compile(
        r"\b\d+\s*(?:[\+\-\*/\^%]|times|plus|minus|into|divided\s+by|\s+[xX]\s+)\s*\d+",
        re.IGNORECASE)),
    (Intent.CALCULATE, 0.85, re.compile(
        r"\b(?:calculate|solve|compute|perform)\s+\d+\s*(?:plus|minus|times|into|divided\s+by|[\+\-\*/xX])\s*\d+",
        re.IGNORECASE)),

    # FILE_SEARCH – search for files/folders, or open/view local files/photos
    (Intent.FILE_SEARCH, 0.90, re.compile(
        r"\b(?:find|search(?:\s+for)?|locate|look\s+for|where\s+is)\b.*?\b(?:file|folder|document|directory|resume|notes)\b",
        re.IGNORECASE)),
    (Intent.FILE_SEARCH, 0.85, re.compile(
        r"\b(?:find|search(?:\s+for)?|locate|look\s+for|where\s+is)\b.*?\b(?:desktop|computer|downloads|documents|pc|laptop)\b",
        re.IGNORECASE)),
    (Intent.FILE_SEARCH, 0.85, re.compile(
        r"\b(?:find|search(?:\s+for)?|locate|look\s+for|where\s+is)\s+\S+\.\w{1,5}\b",
        re.IGNORECASE)),
    (Intent.FILE_SEARCH, 0.85, re.compile(
        r"\b(?:open|view|show)\s+(?:my\s+|the\s+)?(?:photo|picture|image|video|file|document|resume)\b",
        re.IGNORECASE)),

    # LLM_TASK – language reasoning, explanations, information synthesis, document editing
    (Intent.LLM_TASK, 0.90, re.compile(
        r"\b(?:tell\s+me\b|what\s+is\s+going\s+on\b|what\s+is\s+happening\b)",
        re.IGNORECASE)),
    (Intent.LLM_TASK, 0.90, re.compile(
        r"\b(?:summarize|summarise|explain|translate|draft|compose|rewrite|paraphrase|analyze|analyse|write)\b",
        re.IGNORECASE)),
    (Intent.LLM_TASK, 0.90, re.compile(
        r"\b(?:update|edit|revise|modify|improve)\b.*?\b(?:resume|cv|document|essay|article|bio|profile|text)\b",
        re.IGNORECASE)),
]

# Keyword fallback: checked only when no regex pattern matched.
# Maps frozensets of trigger words to (Intent, confidence).
_KEYWORD_TABLE: List[Tuple[Intent, float, List[str]]] = [
    (Intent.OPEN_APP, 0.70, ["open", "launch", "start", "run"]),
    (Intent.OPEN_URL, 0.70, ["website", "url", "browse", "navigate"]),
    (Intent.CALCULATE, 0.70, ["calculate", "compute", "math", "evaluate",
                               "solve", "sum", "add", "subtract",
                               "multiply", "divide"]),
    (Intent.FILE_SEARCH, 0.70, ["find", "search", "locate", "file",
                                 "folder", "directory"]),
    (Intent.LLM_TASK, 0.75, ["summarize", "summarise", "explain",
                              "translate", "write", "compose", "draft",
                              "rewrite", "paraphrase", "analyse",
                              "analyze", "describe", "generate",
                              "create a story", "tell me about",
                              "tell me", "update", "revise"]),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(user_input: str) -> ClassificationResult:
    """Classify a natural-language request into an `Intent`.

    Parameters
    ----------
    user_input : str
        Raw text from the user.

    Returns
    -------
    ClassificationResult
        The best-matching intent with confidence and matched keywords.
        Returns ``Intent.UNKNOWN`` (confidence 0.30) when nothing
        matches confidently.
    """
    if not user_input or not user_input.strip():
        return ClassificationResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            matched_keywords=[],
        )

    text = user_input.strip()
    candidates: List[ClassificationResult] = []

    # --- Phase 1: regex patterns ---
    for intent, confidence, pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            candidates.append(ClassificationResult(
                intent=intent,
                confidence=confidence,
                matched_keywords=[match.group()],
            ))

    # --- Phase 2: keyword fallback (only if no strong pattern hit) ---
    if not candidates:
        text_lower = text.lower()
        for intent, confidence, keywords in _KEYWORD_TABLE:
            hits = [kw for kw in keywords
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)]
            if hits:
                candidates.append(ClassificationResult(
                    intent=intent,
                    confidence=confidence,
                    matched_keywords=hits,
                ))

    # --- Phase 3: pick best candidate ---
    if not candidates:
        return ClassificationResult(
            intent=Intent.UNKNOWN,
            confidence=0.30,
            matched_keywords=[],
        )

    # Sort by confidence descending; break ties by preferring LOCAL-capable
    # intents (OPEN_APP, OPEN_URL, CALCULATE, FILE_SEARCH) over LLM_TASK.
    _local_intents = {Intent.OPEN_APP, Intent.OPEN_URL,
                      Intent.CALCULATE, Intent.FILE_SEARCH}

    def _sort_key(cr: ClassificationResult) -> Tuple[float, int]:
        local_bonus = 1 if cr.intent in _local_intents else 0
        return (cr.confidence, local_bonus)

    candidates.sort(key=_sort_key, reverse=True)
    return candidates[0]
