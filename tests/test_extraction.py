"""Unit tests: upstream two-stage answer extraction."""

from __future__ import annotations

import pytest

from kobalt_eval.extraction import EXTRACTION_REGEX, extract_answer


@pytest.mark.parametrize(
    "text,expected",
    [
        # Multi-match distinct letters -> joined in first-appearance order.
        (
            "먼저 정답은 A입니다 라고 생각했지만, 다시 보니 정답은 C입니다",
            "A, C",
        ),
        # Same letter repeated -> deduplicated.
        (
            "정답은 B입니다. 다시 말해 정답은 B입니다.",
            "B",
        ),
        # Single correct CoT ending.
        (
            "긴 추론 과정 끝에 정답은 H입니다.",
            "H",
        ),
        # No phrase anywhere -> None.
        ("잘 모르겠습니다.", None),
        ("The answer is H.", None),
        # Empty / None input -> None.
        ("", None),
        (None, None),
        # Lowercase letters are not valid answers -> None.
        ("정답은 a입니다", None),
        # Letters outside A-J are filtered out -> None when nothing valid.
        ("정답은 K입니다", None),
        ("정답은 Z입니다", None),
        # Out-of-range letters filtered, valid one kept.
        ("정답은 K, A입니다", "A"),
        # Order of first appearance preserved across matches.
        ("정답은 C입니다 그리고 정답은 A입니다", "C, A"),
        # Three-way repeat with duplicates interleaved.
        ("정답은 A입니다, 정답은 B입니다, 정답은 A입니다", "A, B"),
    ],
)
def test_extract_answer_table(text, expected):
    assert extract_answer(text) == expected


def test_custom_regex_override():
    assert extract_answer("Answer: C", regex=r"Answer:\s*([A-Z])") == "C"
    # Custom regex with no match -> None even though default would match.
    assert extract_answer("정답은 H입니다.", regex=r"Answer:\s*([A-Z])") is None


def test_invalid_regex_falls_back_to_default():
    assert extract_answer("정답은 D입니다", regex="([") == "D"


def test_default_regex_constant():
    assert EXTRACTION_REGEX == r"정답은\s*(.*?)\s*입니다"
