"""Integration tests: CLI run/score/compare + backend factory + key errors."""

from __future__ import annotations

import json

import pytest

from helpers import (
    STUB_OUTPUT_CORRECT_H,
    STUB_OUTPUT_MULTI,
    STUB_OUTPUT_NO_PHRASE,
    StubBackend,
    make_items,
    write_run_config,
)
from kobalt_eval import cli


def _patch_dataset(monkeypatch, items):
    def fake_load(limit=None, **kwargs):
        return list(items[:limit] if limit is not None else items)

    monkeypatch.setattr("kobalt_eval.runner.load_dataset_items", fake_load)
    monkeypatch.setattr(
        "kobalt_eval.runner.get_dataset_revision", lambda **kw: "fake-rev"
    )


def _patch_backend(monkeypatch, outputs):
    stub = StubBackend(outputs)
    monkeypatch.setattr(
        "kobalt_eval.backends.create_backend", lambda config: stub
    )
    return stub


def test_cli_run_score_compare(tmp_path, monkeypatch, capsys):
    items = make_items()
    _patch_dataset(monkeypatch, items)
    _patch_backend(
        monkeypatch,
        [STUB_OUTPUT_CORRECT_H, STUB_OUTPUT_NO_PHRASE, STUB_OUTPUT_MULTI],
    )
    cfg_path = write_run_config(tmp_path / "run.yaml", model="stub-model")
    run_dir = tmp_path / "run-cli"

    assert cli.main(["run", "--config", str(cfg_path), "--out", str(run_dir)]) == 0
    assert (run_dir / "config.snapshot.yaml").exists()
    assert (run_dir / "predictions.jsonl").exists()
    assert (run_dir / "results.json").exists()
    assert (run_dir / "run.log").exists()
    with (run_dir / "predictions.jsonl").open(encoding="utf-8") as f:
        assert len([line for line in f if line.strip()]) == 3

    capsys.readouterr()
    assert cli.main(["score", str(run_dir)]) == 0
    assert "accuracy=" in capsys.readouterr().out

    assert cli.main(["compare", str(run_dir)]) == 0
    out = capsys.readouterr().out
    assert "stub-model" in out
    assert "overall" in out

    md_path = tmp_path / "table.md"
    assert cli.main(["compare", str(run_dir), "--out", str(md_path)]) == 0
    assert "stub-model" in md_path.read_text(encoding="utf-8")

    json_path = tmp_path / "table.json"
    assert cli.main(["compare", str(run_dir), "--out", str(json_path)]) == 0
    assert json.loads(json_path.read_text(encoding="utf-8"))["runs"][0][
        "model"
    ] == "stub-model"


def test_cli_run_with_limit(tmp_path, monkeypatch):
    items = make_items()
    _patch_dataset(monkeypatch, items)
    _patch_backend(monkeypatch, [STUB_OUTPUT_CORRECT_H])
    cfg_path = write_run_config(tmp_path / "run.yaml")
    run_dir = tmp_path / "run-limit"
    assert (
        cli.main(["run", "--config", str(cfg_path), "--limit", "1",
                  "--out", str(run_dir)]) == 0
    )
    with (run_dir / "predictions.jsonl").open(encoding="utf-8") as f:
        assert len([line for line in f if line.strip()]) == 1


def test_cli_run_missing_api_key_errors_cleanly(tmp_path, monkeypatch, capsys):
    """family=api with no key env set -> non-zero exit, clear message.

    Uses the default sequential path: the run_eval API-key pre-flight
    raises before any inference (and before any artifacts are written),
    so the missing-key error surfaces regardless of concurrency.
    No stub patch: the real factory + real OpenAI backend are exercised,
    failing fast on the missing env var before any network call.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _patch_dataset(monkeypatch, make_items())
    cfg_path = write_run_config(
        tmp_path / "run.yaml", family="api", model="gpt-x"
    )
    rc = cli.main(["run", "--config", str(cfg_path),
                   "--out", str(tmp_path / "run-nokey")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err
    assert "not set" in err


def test_cli_score_missing_dir_errors_cleanly(tmp_path, capsys):
    assert cli.main(["score", str(tmp_path / "nope")]) == 1
    assert "error:" in capsys.readouterr().err


def test_backend_factory_mapping():
    from kobalt_eval.backends import create_backend
    from kobalt_eval.backends.api_anthropic import AnthropicBackend
    from kobalt_eval.backends.api_openai import OpenAICompatibleBackend
    from kobalt_eval.backends.transformers_backend import TransformersBackend
    from kobalt_eval.backends.vllm_backend import VLLMBackend
    from kobalt_eval.config import default_run_config

    def cfg_for(family, provider="openai"):
        cfg = default_run_config()
        cfg.backend.family = family
        cfg.backend.api_provider = provider
        cfg.backend.model = "m"
        return cfg

    assert isinstance(create_backend(cfg_for("api", "openai")), OpenAICompatibleBackend)
    assert isinstance(create_backend(cfg_for("api", "anthropic")), AnthropicBackend)
    assert isinstance(create_backend(cfg_for("transformers")), TransformersBackend)
    assert isinstance(create_backend(cfg_for("vllm")), VLLMBackend)


def test_backend_factory_unknown_family():
    from kobalt_eval.backends import create_backend
    from kobalt_eval.config import default_run_config

    cfg = default_run_config()
    cfg.backend.family = "bogus"
    with pytest.raises(ValueError, match="family"):
        create_backend(cfg)


def test_openai_backend_without_key_clean_error(monkeypatch):
    from kobalt_eval.backends.api_openai import OpenAICompatibleBackend
    from kobalt_eval.config import default_run_config

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = default_run_config()
    cfg.backend.model = "gpt-x"
    backend = OpenAICompatibleBackend.from_config(cfg)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY.*not set"):
        backend.generate(
            [[{"role": "user", "content": "hi"}]], cfg
        )


def test_anthropic_backend_without_key_clean_error(monkeypatch):
    from kobalt_eval.backends.api_anthropic import AnthropicBackend
    from kobalt_eval.config import default_run_config

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = default_run_config()
    cfg.backend.model = "claude-x"
    cfg.backend.api_key_env = "ANTHROPIC_API_KEY"
    backend = AnthropicBackend.from_config(cfg)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY.*not set"):
        backend.generate(
            [[{"role": "user", "content": "hi"}]], cfg
        )
