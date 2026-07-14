import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional
from app.config import CATEGORY_GROUPS, CATEGORY_PACKS, DEFAULT_CATEGORIES
from app.db import get_db
from app.game.engine import GameEngine
from app.models import StartGameRequest, StartGameResponse
from app.providers.llm import get_provider as get_llm
from app.providers.messaging import get_provider as get_messaging
from app.validators import validate_custom_categories

_LOG = logging.getLogger(__name__)
router = APIRouter()


@router.get("/categories")
async def get_categories():
    return {
        "categories": DEFAULT_CATEGORIES,
        "groups": CATEGORY_GROUPS,
        "packs": CATEGORY_PACKS,
    }


@router.post("/game/start", response_model=StartGameResponse)
async def start_game(
    req: StartGameRequest,
    user_id: str | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    categories = req.categories or DEFAULT_CATEGORIES

    if req.categories:
        await validate_custom_categories(req.categories)

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
            exclude_words=req.exclude_words,
        )
    except HTTPException:
        raise
    except Exception:
        _LOG.exception("Unexpected error in game/start")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
