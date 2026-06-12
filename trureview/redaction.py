"""
Protected-characteristic redaction. Defense in depth, two layers:

  1. PROMPT layer: the extraction prompt instructs the model to never surface or
     infer protected categories. (Implemented in enrichment.py via the extraction
     system prompt.)
  2. BACKSTOP layer (here): a deterministic scrub over already-extracted text that
     catches obvious protected-category leakage the model might have let through,
     and logs it WITHOUT persisting the protected value.

This is the answer to the hard interview question: "how do you stop the model
factoring in a candidate's age, or a pregnancy post on their blog?" The answer is
not "we hope the prompt holds" — it's a second, inspectable, deterministic gate
with an audit trail.

Backstop is intentionally conservative: it flags and neutralises, and it never
silently drops an item. Everything it touches lands in the redaction_log.
"""

from __future__ import annotations

import re

from .config import PROTECTED_CATEGORIES

# Lightweight signal patterns. This is a backstop, not the primary control, so it
# favours recall (catch likely leakage) and logs for human audit rather than
# attempting perfect precision.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("age", re.compile(r"\b(\d{1,2})\s*(?:years?\s*old|yo|y/o)\b", re.I)),
    ("date of birth", re.compile(r"\b(born in|d\.?o\.?b\.?|date of birth)\b", re.I)),
    ("age", re.compile(r"\b(?:19[3-9]\d|20[01]\d)\s*[-–]\s*present\b")),  # long tenure -> age proxy
    ("pregnancy", re.compile(r"\b(pregnan|maternity leave|expecting a)\b", re.I)),
    ("health", re.compile(r"\b(disability|chronic illness|diagnos(ed|is)|medical condition)\b", re.I)),
    ("religion", re.compile(r"\b(church|mosque|synagogue|temple|parish|muslim|christian|jewish|hindu|sikh)\b", re.I)),
    ("political affiliation", re.compile(r"\b(conservative party|liberal party|ndp|republican|democrat|voted for)\b", re.I)),
    ("marital status", re.compile(r"\b(married|divorced|widowed|my (husband|wife|spouse))\b", re.I)),
    ("national origin", re.compile(r"\b(immigrated from|citizen of|visa status|permanent resident)\b", re.I)),
]


def scrub(text: str) -> tuple[str, list[str]]:
    """Return (cleaned_text, log_entries). Neutralises matches with a [REDACTED:<cat>] token."""
    log: list[str] = []
    cleaned = text
    for category, pattern in _PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(f"[REDACTED:{category}]", cleaned)
            log.append(f"Backstop neutralised a probable '{category}' signal (value not stored).")
    return cleaned, log


def categories_reminder() -> str:
    """Human-readable list for the extraction prompt."""
    return ", ".join(PROTECTED_CATEGORIES)
