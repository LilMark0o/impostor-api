from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import _new_uuid, get_db
from app.models_db import Player

router = APIRouter(prefix="/users", tags=["users"])


class PlayerCreate(BaseModel):
    name: str
    telegram_id: int


class PlayerOut(BaseModel):
    id: str
    name: str
    telegram_id: int


@router.get("/players", response_model=list[PlayerOut])
async def list_players(
    user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Player).where(Player.user_id == user_id))
    return [PlayerOut(id=p.id, name=p.name, telegram_id=p.telegram_id) for p in result.scalars()]


@router.post("/players", response_model=PlayerOut, status_code=201)
async def create_player(
    body: PlayerCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    player = Player(id=_new_uuid(), user_id=user_id, name=body.name, telegram_id=body.telegram_id)
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return PlayerOut(id=player.id, name=player.name, telegram_id=player.telegram_id)


@router.delete("/players/{player_id}", status_code=204)
async def delete_player(
    player_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Player).where(Player.id == player_id, Player.user_id == user_id)
    )
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    await db.delete(player)
    await db.commit()
