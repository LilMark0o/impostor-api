import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator

_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class Mode(str, Enum):
    clasico = "clasico"  # exactly 1 impostor
    caos = "caos"  # random N impostors 0-N
    ciego = "ciego"  # random N, nobody knows how many
    aliados = "aliados"  # 2 impostors know each other
    espejo = "espejo"  # impostor gets a different word from same category
    infiltrados = "infiltrados"
    aleatorio = "aleatorio"
    sin_impostores = "sin_impostores"   # internal; only reachable via aleatorio
    todos_impostores = "todos_impostores"  # internal; only reachable via aleatorio


class Difficulty(str, Enum):
    facil = "facil"
    dificil = "dificil"
    brutal = "brutal"


class Player(BaseModel):
    id: str = ""
    name: str = Field(..., min_length=1, max_length=50)
    telegram_id: int | None = None
    token: str = ""

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        v = _CTRL.sub("", v).strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class StartGameRequest(BaseModel):
    players: list[Player] = Field(..., min_length=2, max_length=20)
    mode: Mode = Mode.caos
    difficulty: Difficulty = Difficulty.dificil
    categories: list[str] | None = Field(None, max_length=15)
    show_category_to_impostor: bool = True
    show_impostor_count: bool = True

    @field_validator("categories")
    @classmethod
    def _clean_categories(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        cleaned = []
        for cat in v:
            cat = _CTRL.sub("", cat).strip()
            if not cat:
                raise ValueError("categories cannot contain empty strings")
            if len(cat) > 100:
                raise ValueError("each category must be 100 characters or fewer")
            cleaned.append(cat)
        return cleaned or None


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
