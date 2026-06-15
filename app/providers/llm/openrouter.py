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
    "Responde SOLO con una palabra específica y concreta, sin puntuación ni explicación."
)


class OpenRouterProvider:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def pick_word(self, category: str) -> str:
        resp = await self._client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": _SOLO_PALABRA},
                {
                    "role": "user",
                    "content": f"Dame una palabra específica de la categoría '{category}'.",
                },
            ],
            max_tokens=10,
        )
        return resp.choices[0].message.content.strip().lower()

    async def pick_hint(self, category: str, word: str, difficulty: str, exclude: list[str]) -> str:
        system = HINT_PROMPTS.get(difficulty, HINT_PROMPTS["dificil"])
        if exclude:
            system += f" No repitas ninguna de estas pistas ya usadas: {', '.join(exclude)}."
        resp = await self._client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Categoría: '{category}', palabra: '{word}'."},
            ],
            max_tokens=15,
        )
        return resp.choices[0].message.content.strip()

    async def pick_mirror_word(self, category: str, exclude: str) -> str:
        resp = await self._client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": _SOLO_PALABRA},
                {
                    "role": "user",
                    "content": (
                        f"Dame una palabra de la categoría '{category}'"
                        f" que sea distinta a '{exclude}'."
                    ),
                },
            ],
            max_tokens=10,
        )
        return resp.choices[0].message.content.strip().lower()
