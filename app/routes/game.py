from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import DEFAULT_CATEGORIES
from app.db import get_db
from app.game.engine import GameEngine
from app.models import StartGameRequest, StartGameResponse
from app.providers.llm import get_provider as get_llm
from app.providers.messaging import get_provider as get_messaging

router = APIRouter()


@router.get("/categories")
async def get_categories():
    return {"categories": DEFAULT_CATEGORIES}


@router.post("/game/start", response_model=StartGameResponse)
async def start_game(
    req: StartGameRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    categories = req.categories or DEFAULT_CATEGORIES
    engine = GameEngine(llm=get_llm(), messaging=get_messaging(), db=db)
    return await engine.run(
        players=req.players,
        categories=categories,
        mode=req.mode,
        difficulty=req.difficulty,
        user_id=user_id,
    )
