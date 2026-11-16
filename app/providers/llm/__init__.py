from typing import Protocol, runtime_checkable

from app.config import OPENAI_API_KEY, OPENROUTER_API_KEY
from app.providers.llm.openrouter import OpenRouterProvider


@runtime_checkable
class LLMProvider(Protocol):
    async def pick_word(self, category: str) -> str: ...

    async def pick_hint(
        self, category: str, word: str, difficulty: str, exclude: list[str]
    ) -> str: ...

    async def pick_mirror_word(self, category: str, exclude: str) -> str: ...


class NoLLMProvider:
    """Stand-in used when no LLM key is configured.

    Every call raises, and every caller already handles that by falling back
    to the static pools and the curated hints. The game must never require a
    key, so this exists instead of crashing while building a client.
    """

    async def pick_word(self, category: str) -> str:
        raise RuntimeError("No LLM provider configured (set OPENAI_API_KEY or OPENROUTER_API_KEY)")

    async def pick_hint(
        self, category: str, word: str, difficulty: str, exclude: list[str]
    ) -> str:
        raise RuntimeError("No LLM provider configured (set OPENAI_API_KEY or OPENROUTER_API_KEY)")

    async def pick_mirror_word(self, category: str, exclude: str) -> str:
        raise RuntimeError("No LLM provider configured (set OPENAI_API_KEY or OPENROUTER_API_KEY)")


def get_provider(name: str = "auto") -> LLMProvider:
    if name == "auto":
        if OPENAI_API_KEY:
            from app.providers.llm.openai_provider import OpenAIProvider

            return OpenAIProvider()
        if OPENROUTER_API_KEY:
            return OpenRouterProvider()
        return NoLLMProvider()
    if name == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        from app.providers.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if name == "openrouter":
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")
        return OpenRouterProvider()
    raise ValueError(f"Unknown LLM provider: {name}")
