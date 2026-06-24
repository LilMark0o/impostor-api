from enum import Enum

from pydantic import BaseModel


class Mode(str, Enum):
    clasico = "clasico"  # exactly 1 impostor
    caos = "caos"  # random N impostors 0-N
    ciego = "ciego"  # random N, nobody knows how many
    aliados = "aliados"  # 2 impostors know each other
    espejo = "espejo"  # impostor gets a different word from same category


class Difficulty(str, Enum):
    facil = "facil"
    dificil = "dificil"
    brutal = "brutal"


class Player(BaseModel):
    id: str = ""
    name: str
    telegram_id: int | None = None
    token: str = ""


class StartGameRequest(BaseModel):
    players: list[Player]
    mode: Mode = Mode.caos
    difficulty: Difficulty = Difficulty.dificil
    categories: list[str] | None = None


class PlayerTokenOut(BaseModel):
    name: str
    token: str


class StartGameResponse(BaseModel):
    category: str
    mode: Mode
    n_impostors: int
    sent: list[str]
    failed: list[str]
    session_id: str
    players: list[PlayerTokenOut]
