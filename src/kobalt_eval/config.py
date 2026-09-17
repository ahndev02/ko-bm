"""Run configuration: dataclasses + YAML/JSON loading + snapshot writing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from kobalt_eval.prompts import SYSTEM_PROMPT, USER_TEMPLATE, prompt_template_hash


@dataclass
class BackendConfig:
    family: str = "api"  # api | transformers | vllm
    model: str = ""
    endpoint: str | None = None  # base_url for OpenAI-compatible endpoints
    engine_opts: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    concurrency: int = 1  # 1 = sequential (upstream default)
    api_key_env: str = "OPENAI_API_KEY"
    api_provider: str = "openai"  # openai | anthropic (only when family == api)


@dataclass
class GenerationConfig:
    do_sample: bool = False
    max_new_tokens: int = 2048


@dataclass
class PromptConfig:
    system: str = SYSTEM_PROMPT
    user_template: str = USER_TEMPLATE


@dataclass
class ExtractionConfig:
    regex: str = r"정답은\s*(.*?)\s*입니다"


@dataclass
class RunConfig:
    backend: BackendConfig = field(default_factory=BackendConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)


def default_run_config() -> RunConfig:
    """Return a RunConfig implementing the official protocol defaults."""
    return RunConfig()


def _coerce_backend(d: dict[str, Any]) -> BackendConfig:
    allowed = {"family", "model", "endpoint", "engine_opts", "max_retries", "concurrency", "api_key_env", "api_provider"}
    filtered = {k: v for k, v in d.items() if k in allowed}
    return BackendConfig(**filtered)


def _coerce_generation(d: dict[str, Any]) -> GenerationConfig:
    allowed = {"do_sample", "max_new_tokens"}
    filtered = {k: v for k, v in d.items() if k in allowed}
    return GenerationConfig(**filtered)


def _coerce_prompt(d: dict[str, Any]) -> PromptConfig:
    allowed = {"system", "user_template"}
    filtered = {k: v for k, v in d.items() if k in allowed}
    return PromptConfig(**filtered)


def _coerce_extraction(d: dict[str, Any]) -> ExtractionConfig:
    allowed = {"regex"}
    filtered = {k: v for k, v in d.items() if k in allowed}
    return ExtractionConfig(**filtered)


def load_config(path: str | Path) -> RunConfig:
    """Load a run config from a YAML (preferred) or JSON file.

    Args:
        path: Path to ``run.yaml`` / ``run.json``.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the file cannot be parsed or has an invalid backend family.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    text = p.read_text(encoding="utf-8")
    data: dict[str, Any]
    if p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # lazy: pyyaml is a core dep but keep import local-safe
        except ImportError as e:
            raise ValueError("PyYAML is required to load YAML configs") from e
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config: top-level mapping expected in {p}")
    backend = _coerce_backend(data.get("backend", {}) or {})
    generation = _coerce_generation(data.get("generation", {}) or {})
    prompt = _coerce_prompt(data.get("prompt", {}) or {})
    extraction = _coerce_extraction(data.get("extraction", {}) or {})
    cfg = RunConfig(backend=backend, generation=generation, prompt=prompt, extraction=extraction)
    validate_config(cfg)
    return cfg


def validate_config(config: RunConfig) -> None:
    """Validate a RunConfig; raises ValueError on invalid values."""
    family = (config.backend.family or "").lower()
    if family not in ("api", "transformers", "vllm"):
        raise ValueError(f"Invalid backend.family: {config.backend.family!r} (expected api|transformers|vllm)")
    if family == "api" and config.backend.api_provider.lower() not in ("openai", "anthropic"):
        raise ValueError(
            f"Invalid backend.api_provider: {config.backend.api_provider!r} (expected openai|anthropic)"
        )
    if config.generation.max_new_tokens is not None and config.generation.max_new_tokens <= 0:
        raise ValueError("generation.max_new_tokens must be positive")
    if not isinstance(config.backend.model, str) or not config.backend.model.strip():
        raise ValueError("backend.model must be a non-empty string")


def config_to_dict(config: RunConfig) -> dict[str, Any]:
    """Convert a RunConfig to a plain dict."""
    return asdict(config)


def snapshot_dict(
    config: RunConfig,
    dataset_revision: str | None = None,
    dataset_name: str = "snunlp/KoBALT-700",
) -> dict[str, Any]:
    """Build the snapshot payload (resolved config + template/dataset hashes)."""
    return {
        "backend": asdict(config.backend),
        "generation": asdict(config.generation),
        "prompt": asdict(config.prompt),
        "extraction": asdict(config.extraction),
        "prompt_template_hash": prompt_template_hash(config.prompt.system, config.prompt.user_template),
        "dataset": {"name": dataset_name, "revision": dataset_revision},
    }


def write_config_snapshot(
    config: RunConfig,
    run_dir: str | Path,
    dataset_revision: str | None = None,
) -> Path:
    """Write ``<run_dir>/config.snapshot.yaml`` and return its path."""
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    payload = snapshot_dict(config, dataset_revision=dataset_revision)
    out = run_path / "config.snapshot.yaml"
    try:
        import yaml

        out.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except ImportError:
        # Fallback to JSON-in-YAML-name is never ideal; write JSON sidecar instead.
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def config_checksum(config: RunConfig) -> str:
    """Stable sha256 of the resolved config dict (for provenance)."""
    blob = json.dumps(config_to_dict(config), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
