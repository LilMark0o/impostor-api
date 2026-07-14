import random

from pydantic import BaseModel

from app.models import Mode, Player
from app.providers.llm import LLMProvider


class RoleAssignment(BaseModel):
    player: Player
    is_impostor: bool
    word: str
    hint: str | None = None
    accomplice: str | None = None  # name of ally in aliados mode


async def assign_roles(
    players: list[Player],
    mode: Mode,
    category: str,
    word: str,
    difficulty: str,
    llm: LLMProvider,
) -> list[RoleAssignment]:
    shuffled = players.copy()
    random.shuffle(shuffled)

    if mode == Mode.clasico:
        n_impostors = 1
    elif mode in (Mode.caos, Mode.ciego):
        n_impostors = random.randint(1, max(1, len(shuffled) // 2))
    elif mode == Mode.aliados:
        n_impostors = 2
    elif mode == Mode.espejo:
        n_impostors = random.randint(1, max(1, len(shuffled) // 2))
    elif mode == Mode.infiltrados:
        n_impostors = 2
    elif mode == Mode.sin_impostores:
        n_impostors = 0
    elif mode == Mode.todos_impostores:
        n_impostors = len(shuffled)
    else:
        n_impostors = 1

    impostors = set(p.name for p in shuffled[:n_impostors])
    accomplices = (
        {p.name: shuffled[(i + 1) % n_impostors].name for i, p in enumerate(shuffled[:n_impostors])}
        if mode == Mode.aliados and n_impostors > 1
        else {}
    )

    mirror_words: dict[str, str] = {}
    if mode in (Mode.espejo, Mode.infiltrados):
        for p in shuffled[:n_impostors]:
            try:
                mirror_words[p.name] = await llm.pick_mirror_word(category, exclude=word)
            except Exception as e:
                print(f"[LLM pick_mirror_word failed] {e} — using fallback")
                mirror_words[p.name] = word + "_alt"

    used_hints: list[str] = []
    assignments: list[RoleAssignment] = []

    for player in shuffled:
        if player.name in impostors:
            if mode == Mode.todos_impostores:
                try:
                    hint = await llm.pick_hint(category, word, difficulty, exclude=used_hints)
                except Exception as e:
                    print(f"[LLM pick_hint failed] {e} — using fallback")
                    hint = "pista"
                used_hints.append(hint)
                assignments.append(
                    RoleAssignment(
                        player=player,
                        is_impostor=True,
                        word="",
                        hint=hint,
                    )
                )
            else:
                try:
                    hint = await llm.pick_hint(category, word, difficulty, exclude=used_hints)
                except Exception as e:
                    print(f"[LLM pick_hint failed] {e} — using fallback")
                    hint = "pista"
                used_hints.append(hint)
                assignments.append(
                    RoleAssignment(
                        player=player,
                        is_impostor=True,
                        word=mirror_words.get(player.name, word),
                        hint=hint,
                        accomplice=accomplices.get(player.name),
                    )
                )
        else:
            assignments.append(
                RoleAssignment(
                    player=player,
                    is_impostor=False,
                    word=word,
                )
            )

    # Shuffle so the impostor's position in the list is random.
    # Without this, impostors always appear first because they are
    # selected from shuffled[:n_impostors] and the loop preserves that order.
    random.shuffle(assignments)
    return assignments
