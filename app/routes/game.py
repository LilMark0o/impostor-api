from fastapi import APIRouter

from app.config import DEFAULT_CATEGORIES
from app.game.engine import GameEngine
from app.models import StartGameRequest, StartGameResponse
from app.providers.llm import get_provider as get_llm
from app.providers.messaging import get_provider as get_messaging

router = APIRouter()


@router.get("/categories")
async def get_categories():
    return {"categories": DEFAULT_CATEGORIES}


@router.post("/game/start", response_model=StartGameResponse)
async def start_game(req: StartGameRequest):
    categories = req.categories or DEFAULT_CATEGORIES
    engine = GameEngine(llm=get_llm(), messaging=get_messaging())
    return await engine.run(
        players=req.players,
        categories=categories,
        mode=req.mode,
        difficulty=req.difficulty,
    )
