import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional
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
    user_id: str | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    categories = req.categories or DEFAULT_CATEGORIES
    engine = GameEngine(llm=get_llm(), messaging=get_messaging(), db=db)
    try:
        return await engine.run(
            players=req.players,
            categories=categories,
            mode=req.mode,
            difficulty=req.difficulty,
            user_id=user_id,
            show_category_to_impostor=req.show_category_to_impostor,
            show_impostor_count=req.show_impostor_count,
        )
    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[game/start ERROR]\n{tb}")
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
