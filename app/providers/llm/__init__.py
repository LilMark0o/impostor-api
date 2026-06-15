from typing import Protocol, runtime_checkable

from app.providers.llm.openrouter import OpenRouterProvider


@runtime_checkable
class LLMProvider(Protocol):
    async def pick_word(self, category: str) -> str: ...

    async def pick_hint(
        self, category: str, word: str, difficulty: str, exclude: list[str]
    ) -> str: ...

    async def pick_mirror_word(self, category: str, exclude: str) -> str: ...


def get_provider(name: str = "openrouter") -> LLMProvider:
    if name == "openrouter":
        return OpenRouterProvider()
    raise ValueError(f"Unknown LLM provider: {name}")
