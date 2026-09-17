"""Backend abstract contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kobalt_eval.config import RunConfig


class AuthenticationFailed(RuntimeError):
    """Fatal auth failure: the server rejected our API key (401/403).

    Raised by API backends when the provider SDK reports an authentication
    or permission error. The runner treats this as fatal and aborts the run
    immediately (no error-record swallowing, no scoring) so a bad key can
    never masquerade as a 0%-accuracy completed run.
    """


class Backend(ABC):
    """Pluggable model runner.

    All backends share one contract so prompt/render/parse/scoring code is
    identical across families:

        generate(messages_list: list[list[dict]], config) -> list[str]
    """

    @abstractmethod
    def generate(
        self,
        messages_list: list[list[dict]],
        config: "RunConfig",
    ) -> list[str]:
        """Generate one raw output string per messages list, in order."""
        raise NotImplementedError

    def generate_one(self, messages: list[dict], config: "RunConfig") -> str:
        """Convenience: generate for a single item."""
        return self.generate([messages], config)[0]
