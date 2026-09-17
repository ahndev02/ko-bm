"""Compare across run directories (reads results.json only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_result(run_dir: str | Path) -> dict[str, Any] | None:
    """Load results.json from a run dir; None (with stderr warning) if missing."""
    path = Path(run_dir) / "results.json"
    if not path.exists():
        print(f"warning: skipping {run_dir}: results.json not found", file=sys.stderr)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"warning: skipping {run_dir}: cannot read results.json ({e})", file=sys.stderr)
        return None


def compare_runs(run_dirs: list[str | Path]) -> dict[str, Any]:
    """Aggregate results.json from each run dir into a comparison payload.

    Returns {"runs": [ {run_dir, model, backend, accuracy, num_items,
    num_correct, by_class: {class: accuracy}} ]}. Runs missing results.json
    are warned-to-stderr and skipped (never fatal).
    """
    rows: list[dict[str, Any]] = []
    for d in run_dirs:
        res = load_result(d)
        if res is None:
            continue
        by_class_raw = res.get("by_class", {}) or {}
        rows.append(
            {
                "run_dir": str(d),
                "model": res.get("model"),
                "backend": res.get("backend"),
                "accuracy": res.get("accuracy", 0.0),
                "num_items": res.get("num_items", 0),
                "num_correct": res.get("num_correct", 0),
                "by_class": {k: v.get("accuracy", 0.0) for k, v in by_class_raw.items()},
            }
        )
    return {"runs": rows}


def format_markdown(comparison: dict[str, Any]) -> str:
    """Render the comparison payload as a markdown table."""
    runs = comparison.get("runs", [])
    if not runs:
        return "No completed runs to compare.\n"
    classes: list[str] = []
    for r in runs:
        for c in r.get("by_class", {}):
            if c not in classes:
                classes.append(c)
    classes.sort()
    header = ["run", "model", "backend", "overall"] + classes
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in runs:
        cells = [
            r.get("run_dir", ""),
            str(r.get("model", "")),
            str(r.get("backend", "")),
            f"{r.get('accuracy', 0.0):.4f}",
        ]
        for c in classes:
            v = r.get("by_class", {}).get(c)
            cells.append(f"{v:.4f}" if isinstance(v, (int, float)) else "n/a")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def compare_and_write(run_dirs: list[str | Path], out: str | Path | None = None) -> str:
    """Compare runs; write to --out file (by suffix) or return stdout text.

    - ``.json`` suffix -> JSON payload.
    - anything else (incl. ``.md``) -> markdown table.
    - ``out=None`` -> markdown table returned (caller prints).

    Returns the rendered text (markdown or JSON).
    """
    comparison = compare_runs(run_dirs)
    if out is None:
        return format_markdown(comparison)
    out_path = Path(out)
    if out_path.suffix.lower() == ".json":
        text = json.dumps(comparison, ensure_ascii=False, indent=2)
    else:
        text = format_markdown(comparison)
    out_path.write_text(text, encoding="utf-8")
    return text
