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


@router.get("/llm-health")
async def llm_health():
    """Diagnose LLM connectivity — remove after debugging."""
    import os
    llm = get_llm()
    key = os.getenv("OPENROUTER_API_KEY", "")
    try:
        word = await llm.pick_word("animal")
        return {"ok": True, "word": word, "key_prefix": key[:8] if key else "MISSING"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "key_prefix": key[:8] if key else "MISSING"}


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
        )
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[game/start ERROR]\n{tb}")
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
