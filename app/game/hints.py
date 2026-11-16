"""Curated, offline hints.

Hints exist so the impostor has something to bluff with, and so the game
works with **no API key**: every hint here is plain text shipped with the
code. When a word has no curated hint the caller may fall back to an LLM
provider, but that path is optional.

A hint must never contain the word itself, nor a word so close that it gives
the answer away. Keep them short, evocative and factual.
"""

from app.config import WORD_HINTS


def pick_hint_from_pool(
    category: str,
    word: str,
    exclude: list[str] | None = None,
) -> str | None:
    """Return the first curated hint for ``word`` that is not in ``exclude``.

    Returns None when the category or the word has no curated hint, or when
    every hint for that word has already been used in this round.
    """
    hints = WORD_HINTS.get(category)
    if not hints:
        return None

    used = exclude or []
    for hint in hints.get(word, []):
        if hint not in used:
            return hint
    return None
