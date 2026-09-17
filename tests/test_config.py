"""Unit tests: run-config loading, validation, defaults, snapshot."""

from __future__ import annotations

import json

import pytest
import yaml

from kobalt_eval.config import (
    RunConfig,
    config_to_dict,
    default_run_config,
    load_config,
    snapshot_dict,
    validate_config,
)
from kobalt_eval.prompts import prompt_template_hash


def test_defaults_match_official_protocol():
    cfg = default_run_config()
    assert cfg.generation.do_sample is False
    assert cfg.generation.max_new_tokens == 2048
    assert cfg.backend.max_retries == 3
    assert cfg.backend.concurrency == 1
    assert cfg.backend.family == "api"


def test_yaml_round_trip(tmp_path):
    cfg = default_run_config()
    cfg.backend.model = "some-model"
    path = tmp_path / "run.yaml"
    path.write_text(yaml.safe_dump(config_to_dict(cfg)), encoding="utf-8")
    loaded = load_config(path)
    assert config_to_dict(loaded) == config_to_dict(cfg)


def test_json_round_trip(tmp_path):
    cfg = default_run_config()
    cfg.backend.family = "transformers"
    cfg.backend.model = "org/tiny"
    path = tmp_path / "run.json"
    path.write_text(json.dumps(config_to_dict(cfg)), encoding="utf-8")
    loaded = load_config(path)
    assert config_to_dict(loaded) == config_to_dict(cfg)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("does-not-exist.yaml")


def test_bad_family_rejected():
    cfg = default_run_config()
    cfg.backend.family = "bogus"
    with pytest.raises(ValueError, match="family"):
        validate_config(cfg)


def test_bad_api_provider_rejected():
    cfg = default_run_config()
    cfg.backend.family = "api"
    cfg.backend.api_provider = "bogus"
    with pytest.raises(ValueError, match="api_provider"):
        validate_config(cfg)


def test_bad_max_new_tokens_rejected():
    cfg = default_run_config()
    cfg.generation.max_new_tokens = 0
    with pytest.raises(ValueError, match="max_new_tokens"):
        validate_config(cfg)


def test_bad_family_in_file_rejected(tmp_path):
    path = tmp_path / "run.yaml"
    path.write_text(yaml.safe_dump({"backend": {"family": "bogus"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="family"):
        load_config(path)


def test_snapshot_contains_template_hash_and_dataset(tmp_path):
    cfg = default_run_config()
    cfg.backend.model = "m"
    snap = snapshot_dict(cfg, dataset_revision="rev-123")
    assert snap["prompt_template_hash"] == prompt_template_hash(
        cfg.prompt.system, cfg.prompt.user_template
    )
    assert snap["dataset"]["name"] == "snunlp/KoBALT-700"
    assert snap["dataset"]["revision"] == "rev-123"
    # Snapshot carries the resolved backend/model for provenance.
    assert snap["backend"]["model"] == "m"


def test_empty_model_rejected():
    cfg = default_run_config()
    cfg.backend.model = ""
    with pytest.raises(ValueError, match="model"):
        validate_config(cfg)
    cfg.backend.model = "   "
    with pytest.raises(ValueError, match="model"):
        validate_config(cfg)
