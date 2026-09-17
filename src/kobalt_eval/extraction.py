"""Upstream two-stage answer extraction (replicated exactly).

Procedure:
  1. ``re.findall(r"정답은\\s*(.*?)\\s*입니다", text)``
  2. From each match, collect uppercase ASCII letters A-Z (upstream collects
     all A-Z), keep only those in the A-J range, in order of first appearance,
     deduplicated.
  3. If any valid letters: return ``", ".join(valid_letters)`` else return None.

A prediction is correct iff the extracted string is exactly one letter equal
to the ground truth.
"""

from __future__ import annotations

import re

EXTRACTION_REGEX: str = r"정답은\s*(.*?)\s*입니다"

_VALID_LETTERS = frozenset("ABCDEFGHIJ")
_LETTER_RE = re.compile(r"[A-Z]")


def extract_answer(text: str | None, regex: str = EXTRACTION_REGEX) -> str | None:
    """Extract the predicted answer from a raw model output.

    Args:
        text: Raw model output (None/empty -> None).
        regex: Extraction regex (defaults to the official one; overridable
            via run config).

    Returns:
        The joined distinct A-J letters (e.g. ``"H"`` or ``"A, C"``), or None
        when no ``정답은 ...입니다`` phrase (or no valid letter) is found.
    """
    if not text:
        return None
    try:
        pattern = re.compile(regex)
    except re.error:
        pattern = re.compile(EXTRACTION_REGEX)
    matches = pattern.findall(text)
    if not matches:
        return None
    seen: list[str] = []
    seen_set: set[str] = set()
    for match in matches:
        if not isinstance(match, str):
            # If the regex has multiple groups, findall returns tuples.
            match = " ".join(match)
        for ch in _LETTER_RE.findall(match):
            if ch in _VALID_LETTERS and ch not in seen_set:
                seen_set.add(ch)
                seen.append(ch)
    if not seen:
        return None
    return ", ".join(seen)
