from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    raw: dict | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    def __init__(self, script: list[str] | dict[str, str]):
        self._script = script
        self._index = 0

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        if isinstance(self._script, list):
            text = self._script[self._index]
            self._index += 1
            return LLMResponse(text=text)

        for key, text in self._script.items():
            if key in prompt:
                return LLMResponse(text=text)
        raise AssertionError(f"FakeLLMProvider: no script entry matches prompt: {prompt!r}")
