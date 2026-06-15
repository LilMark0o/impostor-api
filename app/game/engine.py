import random

from app.game.roles import RoleAssignment, assign_roles
from app.models import Difficulty, Mode, Player, StartGameResponse
from app.providers.llm import LLMProvider
from app.providers.messaging import MessagingProvider


def _build_message(assignment: RoleAssignment, mode: Mode, category: str, n_impostors: int) -> str:
    if not assignment.is_impostor:
        return f"🎯 *Categoría:* {category}\n🔤 *Tu palabra:* {assignment.word.upper()}"

    lines = [f"🎭 *¡Eres el IMPOSTOR!*\n\n📂 {category} — [{assignment.hint}]"]

    if mode == Mode.aliados and assignment.accomplice:
        lines.append(f"🤝 *Tu cómplice:* {assignment.accomplice}")

    if mode == Mode.espejo:
        lines.append(f"🪞 *Tu palabra (diferente):* {assignment.word.upper()}")

    if mode != Mode.ciego:
        lines.append(f"👥 *Impostores en juego:* {n_impostors}")

    return "\n".join(lines)


class GameEngine:
    def __init__(self, llm: LLMProvider, messaging: MessagingProvider):
        self._llm = llm
        self._messaging = messaging

    async def run(
        self,
        players: list[Player],
        categories: list[str],
        mode: Mode = Mode.caos,
        difficulty: Difficulty = Difficulty.dificil,
    ) -> StartGameResponse:
        category = random.choice(categories)
        word = await self._llm.pick_word(category)

        assignments = await assign_roles(
            players=players,
            mode=mode,
            category=category,
            word=word,
            difficulty=difficulty.value,
            llm=self._llm,
        )

        n_impostors = sum(1 for a in assignments if a.is_impostor)
        sent: list[str] = []
        failed: list[str] = []

        for assignment in assignments:
            msg = _build_message(assignment, mode, category, n_impostors)
            ok = await self._messaging.send(assignment.player.telegram_id, msg)
            (sent if ok else failed).append(assignment.player.name)
            status = "✓" if ok else "✗"
            role = "IMPOSTOR" if assignment.is_impostor else "jugador"
            print(f"  {status} {assignment.player.name} ({role})")

        print(
            f"\nModo: {mode.value} | Categoría: {category} "
            f"| Palabra: {word} | Impostores: {n_impostors}"
        )

        return StartGameResponse(
            category=category,
            mode=mode,
            n_impostors=n_impostors,
            sent=sent,
            failed=failed,
        )
