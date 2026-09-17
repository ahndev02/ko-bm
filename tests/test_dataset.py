"""Unit tests: dataset normalization + validation (offline).

The real HF load is covered by one live test gated behind
KOBALT_TEST_LIVE=1 so CI stays offline-deterministic.
"""

from __future__ import annotations

import os

import pytest

from helpers import make_valid_items
from kobalt_eval.dataset import (
    DATASET_NAME,
    EXPECTED_COUNT,
    VALID_ANSWERS,
    VALID_CLASSES,
    normalize_item,
    validate_items,
)


def test_normalize_item_maps_hf_row(raw_items, items):
    assert normalize_item(raw_items[0]) == items[0]
    rec = normalize_item(raw_items[2])
    assert rec == {
        "id": "test-id-0003",
        "class": "Morphology",
        "subclass": "Agreement",
        "question": rec["question"],
        "ground_truth": "B",
        "level": 3,
        "sampling_yn": 1,
    }
    assert isinstance(rec["level"], int)
    assert isinstance(rec["sampling_yn"], int)


def test_valid_700_passes():
    validate_items(make_valid_items(700))


def test_wrong_count_rejected():
    with pytest.raises(ValueError, match="700"):
        validate_items(make_valid_items(3))


def test_invalid_answer_letter_rejected():
    items = make_valid_items(700)
    items[10]["ground_truth"] = "K"
    with pytest.raises(ValueError, match="Answer"):
        validate_items(items)


def test_invalid_class_rejected():
    items = make_valid_items(700)
    items[10]["class"] = "Syntaxx"
    with pytest.raises(ValueError, match="Class"):
        validate_items(items)


def test_bad_level_rejected():
    items = make_valid_items(700)
    items[10]["level"] = 9
    with pytest.raises(ValueError, match="Level"):
        validate_items(items)


def test_empty_question_rejected():
    items = make_valid_items(700)
    items[10]["question"] = ""
    with pytest.raises(ValueError, match="Question"):
        validate_items(items)


def test_duplicate_id_rejected():
    items = make_valid_items(700)
    items[10]["id"] = items[0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_items(items)


def test_schema_constants():
    assert DATASET_NAME == "snunlp/KoBALT-700"
    assert EXPECTED_COUNT == 700
    assert set(VALID_CLASSES) == {
        "Syntax",
        "Semantics",
        "Pragmatics",
        "Phonetics/Phonology",
        "Morphology",
    }
    assert VALID_ANSWERS == tuple("ABCDEFGHIJ")


@pytest.mark.skipif(
    os.environ.get("KOBALT_TEST_LIVE") != "1",
    reason="live HF load is manual-only (needs network); set KOBALT_TEST_LIVE=1",
)
def test_live_dataset_load():
    """Real load from HuggingFace: 700 items, valid classes/answers."""
    from kobalt_eval.dataset import load_dataset_items

    items = load_dataset_items()
    assert len(items) == EXPECTED_COUNT
    assert {it["class"] for it in items} == set(VALID_CLASSES)
    assert all(it["ground_truth"] in VALID_ANSWERS for it in items)
    validate_items(items)
