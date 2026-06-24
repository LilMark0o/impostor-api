from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models_db import GamePlayerResult, GameSession, Player

router = APIRouter()


class RevealResponse(BaseModel):
    state: Literal["waiting", "ready"]
    player_name: str
    session_id: str | None = None
    is_impostor: bool | None = None
    category: str | None = None


@router.get("/p/{token}", response_model=RevealResponse)
async def reveal(token: str, db: AsyncSession = Depends(get_db)):
    # 1. Look up player by token
    result = await db.execute(select(Player).where(Player.token == token))
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    # 2. Find most recent game result for this player
    stmt = (
        select(GamePlayerResult, GameSession)
        .join(GameSession, GamePlayerResult.session_id == GameSession.id)
        .where(GamePlayerResult.player_id == player.id)
        .order_by(GameSession.created_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()

    # 3. No game yet → waiting
    if row is None:
        return RevealResponse(state="waiting", player_name=player.name)

    game_result, _session = row

    # 4. Game found → ready
    return RevealResponse(
        state="ready",
        player_name=game_result.player_name,
        session_id=game_result.session_id,
        is_impostor=game_result.is_impostor,
        category=game_result.category_shown if not game_result.is_impostor else None,
    )
