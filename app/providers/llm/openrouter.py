from openai import AsyncOpenAI

from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

HINT_PROMPTS = {
    "facil": (
        "Dada una palabra y su categoría, da una pista descriptiva de máximo 3 palabras "
        "que ayude al impostor a parecer que sabe, sin revelar la palabra exacta."
    ),
    "dificil": (
        "Dada una palabra y su categoría, da una pista críptica de máximo 3 palabras. "
        "NO debe revelar ni la palabra ni la categoría obvia. Asociación indirecta."
    ),
    "brutal": (
        "Dada una palabra y su categoría, da UNA SOLA palabra completamente abstracta "
        "o metafórica. Que sea casi imposible de deducir. Sin relación obvia."
    ),
}

_SOLO_PALABRA = (
    "Reply with exactly ONE word. No punctuation, no explanation, no sentences. "
    "Just the word itself."
)

# Models tried in order when one is rate-limited or unavailable
_FALLBACK_MODELS = [
    OPENROUTER_MODEL,
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]


def _first_word(text: str) -> str:
    """Extract the first token from a model response, stripping punctuation."""
    clean = text.strip().split()[0] if text.strip() else text
    return clean.strip(".,!?;:'\"()[]").lower()


class OpenRouterProvider:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def _complete(self, messages: list[dict], max_tokens: int = 10) -> str:
        """Try models in order, returning first successful response."""
        last_err: Exception | None = None
        seen: set[str] = set()
        for model in _FALLBACK_MODELS:
            if model in seen:
                continue
            seen.add(model)
            try:
                resp = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                )
                print(f"[LLM] model={model} ok")
                return resp.choices[0].message.content
            except Exception as e:
                print(f"[LLM] model={model} failed: {e}")
                last_err = e
        raise last_err or RuntimeError("All LLM models failed")

    async def pick_word(self, category: str) -> str:
        text = await self._complete([
            {"role": "system", "content": _SOLO_PALABRA},
            {"role": "user", "content": f"Dame una palabra específica de la categoría '{category}'."},
        ])
        return _first_word(text)

    async def pick_hint(self, category: str, word: str, difficulty: str, exclude: list[str]) -> str:
        system = HINT_PROMPTS.get(difficulty, HINT_PROMPTS["dificil"])
        if exclude:
            system += f" No repitas ninguna de estas pistas ya usadas: {', '.join(exclude)}."
        text = await self._complete([
            {"role": "system", "content": system},
            {"role": "user", "content": f"Categoría: '{category}', palabra: '{word}'."},
        ], max_tokens=15)
        return text.strip()

    async def pick_mirror_word(self, category: str, exclude: str) -> str:
        text = await self._complete([
            {"role": "system", "content": _SOLO_PALABRA},
            {"role": "user", "content": (
                f"Dame una palabra de la categoría '{category}'"
                f" que sea distinta a '{exclude}'."
            )},
        ])
        return _first_word(text)
