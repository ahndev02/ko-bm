"""Unit tests: multi-run comparison over fixture run dirs."""

from __future__ import annotations

import json

from helpers import write_results_run
from kobalt_eval.reporting import (
    compare_and_write,
    compare_runs,
    format_markdown,
)


def test_compare_rows_present(tmp_path):
    d1 = write_results_run(tmp_path / "run-a", model="model-a", accuracy=0.6)
    d2 = write_results_run(
        tmp_path / "run-b",
        model="model-b",
        accuracy=0.25,
        num_items=4,
        num_correct=1,
        by_class={"Syntax": {"n": 4, "correct": 1, "accuracy": 0.25}},
    )
    comparison = compare_runs([d1, d2])
    assert len(comparison["runs"]) == 2
    row = comparison["runs"][0]
    assert row["model"] == "model-a"
    assert row["backend"] == "api"
    assert row["accuracy"] == 0.6
    assert row["num_items"] == 4
    assert row["num_correct"] == 2
    assert row["by_class"]["Syntax"] == 0.5
    assert comparison["runs"][1]["by_class"]["Syntax"] == 0.25


def test_missing_results_json_warns_and_skips(tmp_path, capsys):
    good = write_results_run(tmp_path / "run-a", model="model-a")
    missing = tmp_path / "run-broken"
    missing.mkdir()
    comparison = compare_runs([good, missing])
    assert len(comparison["runs"]) == 1
    assert comparison["runs"][0]["model"] == "model-a"
    err = capsys.readouterr().err
    assert "warning" in err
    assert "results.json" in err


def test_corrupt_results_json_warns_and_skips(tmp_path, capsys):
    bad = tmp_path / "run-bad"
    bad.mkdir()
    (bad / "results.json").write_text("{not json", encoding="utf-8")
    assert compare_runs([bad]) == {"runs": []}
    assert "warning" in capsys.readouterr().err


def test_markdown_output_format(tmp_path):
    d1 = write_results_run(tmp_path / "run-a", model="model-a", accuracy=0.6)
    out = tmp_path / "table.md"
    text = compare_and_write([d1], out=out)
    assert "model-a" in text
    assert "overall" in text
    assert "0.6000" in text
    assert out.read_text(encoding="utf-8") == text


def test_json_output_format(tmp_path):
    d1 = write_results_run(tmp_path / "run-a", model="model-a")
    out = tmp_path / "table.json"
    text = compare_and_write([d1], out=out)
    payload = json.loads(text)
    assert payload["runs"][0]["model"] == "model-a"
    assert json.loads(out.read_text(encoding="utf-8")) == payload


def test_stdout_default_returns_markdown(tmp_path):
    d1 = write_results_run(tmp_path / "run-a", model="model-a")
    text = compare_and_write([d1], out=None)
    assert text.startswith("|")
    assert "model-a" in text


def test_empty_comparison_message():
    assert format_markdown({"runs": []}) == "No completed runs to compare.\n"
