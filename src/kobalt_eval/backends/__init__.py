"""Backend factory: family string -> backend instance."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kobalt_eval.backends.base import AuthenticationFailed, Backend

if TYPE_CHECKING:
    from kobalt_eval.config import RunConfig


def create_backend(config: "RunConfig") -> Backend:
    """Instantiate the backend described by a RunConfig.

    Mapping:
      family=api + api_provider=openai (default) -> OpenAICompatibleBackend
      family=api + api_provider=anthropic        -> AnthropicBackend
      family=transformers                        -> TransformersBackend
      family=vllm                                -> VLLMBackend

    All heavy imports are lazy (inside backend constructors/methods) so the
    core package imports cleanly without optional deps installed.
    """
    family = (config.backend.family or "").lower()
    if family == "api":
        provider = (config.backend.api_provider or "openai").lower()
        if provider == "anthropic":
            from kobalt_eval.backends.api_anthropic import AnthropicBackend

            return AnthropicBackend.from_config(config)
        if provider == "openai":
            from kobalt_eval.backends.api_openai import OpenAICompatibleBackend

            return OpenAICompatibleBackend.from_config(config)
        raise ValueError(f"Unknown api_provider: {config.backend.api_provider!r}")
    if family == "transformers":
        from kobalt_eval.backends.transformers_backend import TransformersBackend

        return TransformersBackend.from_config(config)
    if family == "vllm":
        from kobalt_eval.backends.vllm_backend import VLLMBackend

        return VLLMBackend.from_config(config)
    raise ValueError(f"Unknown backend.family: {config.backend.family!r}")


__all__ = ["AuthenticationFailed", "Backend", "create_backend"]
