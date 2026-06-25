from typing import Protocol, runtime_checkable

from app.config import OPENAI_API_KEY
from app.providers.llm.openrouter import OpenRouterProvider


@runtime_checkable
class LLMProvider(Protocol):
    async def pick_word(self, category: str) -> str: ...

    async def pick_hint(
        self, category: str, word: str, difficulty: str, exclude: list[str]
    ) -> str: ...

    async def pick_mirror_word(self, category: str, exclude: str) -> str: ...


def get_provider(name: str = "auto") -> LLMProvider:
    if name == "auto":
        if OPENAI_API_KEY:
            from app.providers.llm.openai_provider import OpenAIProvider
            return OpenAIProvider()
        return OpenRouterProvider()
    if name == "openai":
        from app.providers.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "openrouter":
        return OpenRouterProvider()
    raise ValueError(f"Unknown LLM provider: {name}")
