"""Dataset loading + integrity validation for snunlp/KoBALT-700."""

from __future__ import annotations

from typing import Any

DATASET_NAME: str = "snunlp/KoBALT-700"
DATASET_SUBSET: str = "kobalt_v1"
DATASET_SPLIT: str = "raw"
EXPECTED_COUNT: int = 700

VALID_CLASSES: tuple[str, ...] = (
    "Syntax",
    "Semantics",
    "Pragmatics",
    "Phonetics/Phonology",
    "Morphology",
)

VALID_ANSWERS: tuple[str, ...] = tuple("ABCDEFGHIJ")
VALID_LEVELS: tuple[int, ...] = (1, 2, 3)


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize one HF record to the harness item dict.

    Returns keys: id, class, subclass, question, ground_truth, level, sampling_yn.
    """
    return {
        "id": str(raw["ID"]),
        "class": raw["Class"],
        "subclass": raw["Subclass"],
        "question": raw["Question"],
        "ground_truth": raw["Answer"],
        "level": int(raw["Level"]),
        "sampling_yn": int(raw.get("Sampling_YN", 0)),
    }


def validate_items(items: list[dict[str, Any]]) -> None:
    """Validate integrity of normalized items.

    Checks: exactly 700 items, 5 Class values present, answers in A-J,
    levels in 1-3, non-empty questions, unique IDs.

    Raises:
        ValueError: On any integrity violation.
    """
    if len(items) != EXPECTED_COUNT:
        raise ValueError(f"Dataset integrity: expected {EXPECTED_COUNT} items, got {len(items)}")
    classes = {it["class"] for it in items}
    if set(classes) != set(VALID_CLASSES):
        raise ValueError(
            f"Dataset integrity: expected Class values {sorted(VALID_CLASSES)}, got {sorted(classes)}"
        )
    seen_ids: set[str] = set()
    for it in items:
        if it["ground_truth"] not in VALID_ANSWERS:
            raise ValueError(f"Dataset integrity: invalid Answer {it['ground_truth']!r} for id {it['id']!r}")
        if it["level"] not in VALID_LEVELS:
            raise ValueError(f"Dataset integrity: invalid Level {it['level']!r} for id {it['id']!r}")
        if not it["question"]:
            raise ValueError(f"Dataset integrity: empty Question for id {it['id']!r}")
        if it["id"] in seen_ids:
            raise ValueError(f"Dataset integrity: duplicate ID {it['id']!r}")
        seen_ids.add(it["id"])


def load_dataset_items(
    limit: int | None = None,
    split: str = DATASET_SPLIT,
    name: str = DATASET_NAME,
    subset: str = DATASET_SUBSET,
    validate: bool = True,
) -> list[dict[str, Any]]:
    """Load KoBALT-700 items from HuggingFace (with local HF caching).

    Args:
        limit: Optional subset size (first N items in dataset order).
        split: HF split (default ``raw``).
        name: HF dataset repo id.
        subset: HF config/subset name (default ``kobalt_v1``).
        validate: Run integrity validation (skipped when limit is set, since a
            subset cannot satisfy the 700-item count check).

    Raises:
        RuntimeError: With a clear message when the dataset cannot be loaded
            (e.g. no network, missing ``datasets`` package).
    """
    try:
        from datasets import load_dataset  # lazy: core dep, but keep import local
    except ImportError as e:
        raise RuntimeError(
            "The 'datasets' package is required to load KoBALT-700. Install it with "
            "`pip install datasets` or `uv sync`."
        ) from e
    try:
        ds = load_dataset(name, subset, split=split)
    except Exception as e:
        raise RuntimeError(
            f"Failed to load dataset {name!r} (subset={subset!r}, split={split!r}). "
            f"Check network access to HuggingFace Hub and local HF cache. Original error: {e}"
        ) from e
    items = [normalize_item(dict(row)) for row in ds]
    if validate and limit is None:
        validate_items(items)
    if limit is not None:
        items = items[:limit]
    return items


def get_dataset_revision(
    name: str = DATASET_NAME,
    subset: str = DATASET_SUBSET,
    split: str = DATASET_SPLIT,
) -> str | None:
    """Best-effort dataset revision hash for run provenance.

    Returns None when it cannot be determined (offline, API change, ...).
    Never raises.
    """
    try:
        from datasets import load_dataset

        ds = load_dataset(name, subset, split=split)
        info = getattr(ds, "info", None)
        for attr in ("download_checksum", "dataset_name"):
            _ = attr  # reserved for future provenance fields
        version = getattr(info, "version", None) if info is not None else None
        if version is not None:
            return str(version)
        # Fingerprint of the processed split is a stable local proxy.
        fingerprint = getattr(ds, "_fingerprint", None)
        if fingerprint:
            return str(fingerprint)
        return None
    except Exception:
        return None
