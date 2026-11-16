"""Curated hints: content integrity and role wiring."""

import pytest

from app.config import WORD_HINTS, WORD_POOLS
from app.game.hints import pick_hint_from_pool


def _all_words(category: str) -> set[str]:
    return {w for words in WORD_POOLS[category].values() for w in words}


def test_hint_for_known_word():
    hint = pick_hint_from_pool("ganador del Balón de Oro", "Messi", [])
    assert hint is not None
    assert "Messi" not in hint


def test_hint_round_robin_skips_used():
    first = pick_hint_from_pool("ganador del Balón de Oro", "Messi", [])
    second = pick_hint_from_pool("ganador del Balón de Oro", "Messi", [first])
    assert first != second
    # Third call: both used up → nothing left to give.
    assert pick_hint_from_pool("ganador del Balón de Oro", "Messi", [first, second]) is None


def test_hint_unknown_category_or_word():
    assert pick_hint_from_pool("categoría inventada", "Messi", []) is None
    assert pick_hint_from_pool("ganador del Balón de Oro", "Bakayoko", []) is None


def test_every_hint_belongs_to_a_real_pool_word():
    """A hint attached to a word the pool never serves is dead content."""
    orphans = []
    for category, hints in WORD_HINTS.items():
        assert category in WORD_POOLS, f"hint category not in WORD_POOLS: {category}"
        words = _all_words(category)
        for word in hints:
            if word not in words:
                orphans.append(f"{category} → {word}")
    assert not orphans, f"hints for words outside the pool: {orphans}"


def test_hints_never_contain_their_own_word():
    leaks = []
    for category, hints in WORD_HINTS.items():
        for word, hint_list in hints.items():
            if len(word) < 4:
                continue
            for hint in hint_list:
                if word.lower() in hint.lower():
                    leaks.append(f"{category} → {word}: {hint}")
    assert not leaks, f"hints leaking the word: {leaks}"


def test_hints_are_unique_within_a_word():
    for category, hints in WORD_HINTS.items():
        for word, hint_list in hints.items():
            assert len(hint_list) == len(set(hint_list)), f"duplicate hint for {category}/{word}"


def test_new_categories_have_hints_and_pools():
    """The categories added alongside the hint system must be fully usable."""
    for category in [
        "campeón del mundo",
        "campeón de la Champions League",
        "Bota de Oro de un Mundial",
        "apodo de futbolista",
        "portero legendario",
        "defensa legendario",
        "mediocampista legendario",
        "delantero legendario",
        "planeta del sistema solar",
        "instrumento musical",
    ]:
        assert category in WORD_POOLS, category
        words = _all_words(category)
        assert len(words) >= 5, f"{category} has too few words"
        missing = [w for w in words if w not in WORD_HINTS.get(category, {})]
        assert not missing, f"{category} words without a hint: {missing}"


def test_hints_are_a_single_word():
    """Product rule: a hint is one word, not a sentence."""
    offenders = []
    for category, hints in WORD_HINTS.items():
        for word, hint_list in hints.items():
            for hint in hint_list:
                if len(hint.split()) != 1:
                    offenders.append(f"{category} → {word}: {hint!r}")
    assert not offenders, f"hints must be one word: {offenders}"


def test_short_version_categories_use_year_and_winner():
    """campeón del mundo / Champions / Bota de Oro name a year and a winner."""
    for category in [
        "campeón del mundo",
        "campeón de la Champions League",
        "Bota de Oro de un Mundial",
    ]:
        for word in _all_words(category):
            year, _, entity = word.partition(" ")
            assert year.isdigit() and len(year) == 4, f"{category}: {word!r}"
            assert entity, f"{category}: {word!r}"


def test_porteros_has_at_least_twenty():
    assert len(_all_words("portero legendario")) >= 20


def test_nicknames_cover_famous_and_obscure():
    assert len(_all_words("apodo de futbolista")) >= 30


@pytest.mark.asyncio
async def test_assign_roles_prefers_curated_hint(mock_llm):
    """With a curated hint available, the LLM is not called at all."""
    from app.game.roles import assign_roles
    from app.models import Difficulty, Mode, Player

    players = [Player(name="A"), Player(name="B"), Player(name="C")]
    result = await assign_roles(
        players=players,
        mode=Mode.clasico,
        category="ganador del Balón de Oro",
        word="Messi",
        difficulty=Difficulty.dificil.value,
        llm=mock_llm,
    )
    impostor = next(r for r in result if r.is_impostor)
    assert impostor.hint in WORD_HINTS["ganador del Balón de Oro"]["Messi"]
    mock_llm.pick_hint.assert_not_called()


@pytest.mark.asyncio
async def test_assign_roles_falls_back_to_llm_without_curated_hint(mock_llm):
    from app.game.roles import assign_roles
    from app.models import Difficulty, Mode, Player

    players = [Player(name="A"), Player(name="B"), Player(name="C")]
    result = await assign_roles(
        players=players,
        mode=Mode.clasico,
        category="categoría personalizada",
        word="algo",
        difficulty=Difficulty.dificil.value,
        llm=mock_llm,
    )
    impostor = next(r for r in result if r.is_impostor)
    assert impostor.hint == "fiel"
    mock_llm.pick_hint.assert_awaited()


@pytest.mark.asyncio
async def test_assign_roles_without_hint_and_without_llm(mock_llm):
    """No curated hint and a failing LLM must not crash the round."""
    from app.game.roles import assign_roles
    from app.models import Difficulty, Mode, Player

    mock_llm.pick_hint.side_effect = RuntimeError("no key")
    players = [Player(name="A"), Player(name="B"), Player(name="C")]
    result = await assign_roles(
        players=players,
        mode=Mode.clasico,
        category="categoría personalizada",
        word="algo",
        difficulty=Difficulty.dificil.value,
        llm=mock_llm,
    )
    impostor = next(r for r in result if r.is_impostor)
    assert impostor.hint is None
