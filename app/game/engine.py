import random

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DIFFICULTY_FALLBACK, WORD_POOLS
from app.db import _new_uuid
from app.game.roles import RoleAssignment, assign_roles
from app.models import Difficulty, Mode, Player, PlayerTokenOut, StartGameResponse
from app.models_db import GamePlayerResult, GameSession
from app.models_db import Player as PlayerRecord
from app.providers.llm import LLMProvider
from app.providers.messaging import MessagingProvider

_INTERNAL_MODES = frozenset({Mode.sin_impostores, Mode.todos_impostores})

_ALEATORIO_POOL = [
    Mode.clasico,
    Mode.caos,
    Mode.aliados,
    Mode.espejo,
    Mode.infiltrados,
    Mode.sin_impostores,
    Mode.todos_impostores,
]


def _mode_is_eligible(m: Mode, n: int) -> bool:
    if m == Mode.aliados:
        return n >= 4
    if m == Mode.infiltrados:
        return n >= 5
    return True


def pick_word_from_pool(
    category: str,
    difficulty: str,
    exclude: set[str],
) -> str | None:
    """
    Try to pick a word from the static pool for this category.

    Tries difficulty sub-pools in fallback order:
      facil   → f → d → b
      dificil → d → b → f
      brutal  → b → f → d

    If the selected sub-pool is fully exhausted (all words in exclude),
    falls back to the next tier. If ALL words are excluded, picks randomly
    from the full pool ignoring the exclusion list (avoids deadlock on
    long play sessions).

    Returns None if the category has no pool (custom category → use LLM).
    """
    pool = WORD_POOLS.get(category)
    if not pool:
        return None

    order = DIFFICULTY_FALLBACK.get(difficulty, ["d", "f", "b"])

    # Try each tier in fallback order (case-insensitive exclusion)
    for tier in order:
        candidates = [w for w in pool.get(tier, []) if w.lower() not in exclude]
        if candidates:
            return random.choice(candidates)

    # All words exhausted — pick from full pool ignoring exclusion
    all_words = [w for tier_words in pool.values() for w in tier_words]
    if all_words:
        print(f"[Pool] All words exhausted for '{category}', cycling — ignoring exclude list")
        return random.choice(all_words)

    return None


def _build_message(
    assignment: RoleAssignment,
    mode: Mode,
    category: str,
    n_impostors: int,
    show_category_to_impostor: bool = True,
    show_impostor_count: bool = True,
) -> str:
    if not assignment.is_impostor:
        return (
            f"🎯 *Categoría:* {category}\n🔤 *Tu palabra:* {assignment.word.upper()}"
        )

    if mode == Mode.todos_impostores:
        return f"🎭 *¡Todos son impostores!*\n\n📂 {category} — [{assignment.hint}]"

    lines = ["🎭 *¡Eres el IMPOSTOR!*"]

    if show_category_to_impostor:
        lines.append(f"\n📂 {category} — [{assignment.hint}]")
    else:
        lines.append(f"\n🕵️ Pista: [{assignment.hint}]")

    if mode == Mode.aliados and assignment.accomplice:
        lines.append(f"🤝 *Tu cómplice:* {assignment.accomplice}")

    if mode in (Mode.espejo, Mode.infiltrados):
        lines.append(f"🪞 *Tu palabra (diferente):* {assignment.word.upper()}")

    if show_impostor_count:
        lines.append(f"👥 *Impostores en juego:* {n_impostors}")

    return "\n".join(lines)


class GameEngine:
    def __init__(self, llm: LLMProvider, messaging: MessagingProvider, db: AsyncSession):
        self._llm = llm
        self._messaging = messaging
        self._db = db

    def _new_anon_player(self, p: Player) -> tuple[str, str]:
        pid, ptok = _new_uuid(), _new_uuid()
        self._db.add(
            PlayerRecord(id=pid, user_id=None, name=p.name, telegram_id=p.telegram_id, token=ptok)
        )
        return pid, ptok

    async def run(
        self,
        players: list[Player],
        categories: list[str],
        mode: Mode = Mode.caos,
        difficulty: Difficulty = Difficulty.dificil,
        user_id: str | None = None,
        show_category_to_impostor: bool = True,
        show_impostor_count: bool = True,
        exclude_words: list[str] | None = None,
    ) -> StartGameResponse:
        if mode in _INTERNAL_MODES:
            raise HTTPException(
                status_code=400, detail="This mode cannot be selected directly"
            )

        if mode == Mode.aliados and len(players) < 4:
            raise HTTPException(
                status_code=400, detail="aliados requires at least 4 players"
            )
        if mode == Mode.infiltrados and len(players) < 5:
            raise HTTPException(
                status_code=400, detail="infiltrados requires at least 5 players"
            )

        resolved_mode = mode
        if mode == Mode.aleatorio:
            eligible = [m for m in _ALEATORIO_POOL if _mode_is_eligible(m, len(players))]
            resolved_mode = random.choice(eligible)

        category = random.choice(categories)
        excluded: set[str] = {w.lower() for w in (exclude_words or [])}

        # Try static pool first; fall back to LLM for custom categories
        word = pick_word_from_pool(category, difficulty.value, excluded)
        source = "pool"

        if word is None:
            source = "llm"
            try:
                word = await self._llm.pick_word(category)
            except Exception as e:
                print(f"[LLM pick_word failed] {e} — using hardcoded fallback")
                _FALLBACK: dict[str, list[str]] = {
                    "animal": ["León", "Jirafa", "Pingüino"],
                    "país": ["Brasil", "Japón", "Alemania"],
                    "fruta": ["Mango", "Sandía", "Maracuyá"],
                    "profesión": ["Arquitecto", "Enfermero", "Piloto"],
                    "marca de ropa": ["Nike", "Adidas", "Zara"],
                    "superhéroe": ["Batman", "Spider-Man", "Wonder Woman"],
                    "empresa de tecnología": ["Google", "Apple", "Amazon"],
                    "marca de carros": ["Toyota", "BMW", "Ferrari"],
                    "jugador de fútbol famoso": ["Messi", "Ronaldo", "Neymar"],
                }
                defaults = ["Messi", "Google", "Brasil", "León", "Nike"]
                word = random.choice(_FALLBACK.get(category, defaults))

        print(
            f"[Word] source={source} category='{category}' word='{word}' "
            f"difficulty={difficulty.value}"
        )

        assignments = await assign_roles(
            players=players,
            mode=resolved_mode,
            category=category,
            word=word,
            difficulty=difficulty.value,
            llm=self._llm,
        )

        n_impostors = sum(1 for a in assignments if a.is_impostor)
        sent: list[str] = []
        failed: list[str] = []

        for assignment in assignments:
            if assignment.player.telegram_id is None:
                failed.append(assignment.player.name)
                continue
            msg = _build_message(
                assignment, resolved_mode, category, n_impostors,
                show_category_to_impostor, show_impostor_count,
            )
            ok = await self._messaging.send(assignment.player.telegram_id, msg)
            (sent if ok else failed).append(assignment.player.name)
            status = "✓" if ok else "✗"
            role = "IMPOSTOR" if assignment.is_impostor else "jugador"
            print(f"  {status} {assignment.player.name} ({role})")

        resolved: list[tuple[str, str]] = []
        for assignment in assignments:
            p = assignment.player
            if p.id and p.token:
                resolved.append((p.id, p.token))
            elif p.token:
                row = await self._db.execute(
                    select(PlayerRecord).where(PlayerRecord.token == p.token)
                )
                existing = row.scalar_one_or_none()
                if existing:
                    resolved.append((existing.id, existing.token))
                else:
                    resolved.append(self._new_anon_player(p))
            else:
                resolved.append(self._new_anon_player(p))

        await self._db.flush()

        session = GameSession(
            id=_new_uuid(),
            user_id=user_id,
            category=category,
            mode=resolved_mode.value,
            difficulty=difficulty.value,
            n_impostors=n_impostors,
        )
        self._db.add(session)

        player_tokens: list[PlayerTokenOut] = []
        for assignment, (pid, ptok) in zip(assignments, resolved):
            category_shown = assignment.word if not assignment.is_impostor else ""
            self._db.add(
                GamePlayerResult(
                    id=_new_uuid(),
                    session_id=session.id,
                    player_id=pid,
                    player_name=assignment.player.name,
                    is_impostor=assignment.is_impostor,
                    category_shown=category_shown,
                )
            )
            player_tokens.append(PlayerTokenOut(name=assignment.player.name, token=ptok))

        await self._db.commit()

        print(
            f"\nModo: {resolved_mode.value} | Categoría: {category} "
            f"| Palabra: {word} | Impostores: {n_impostors}"
        )

        return StartGameResponse(
            category=category,
            mode=resolved_mode,
            n_impostors=n_impostors,
            sent=sent,
            failed=failed,
            session_id=session.id,
            players=player_tokens,
            word=word,
        )
