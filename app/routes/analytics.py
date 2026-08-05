from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models_db import GamePlayerResult, GameSession

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DailyStat(BaseModel):
    date: str
    sessions: int
    unique_players: int
    by_mode: dict[str, int]
    by_category: dict[str, int]


class PlayerRoundOut(BaseModel):
    player_name: str
    is_impostor: bool
    word_shown: str


class SessionDetail(BaseModel):
    id: str
    created_at: datetime
    mode: str
    category: str
    difficulty: str
    n_impostors: int
    players: list[PlayerRoundOut]


@router.get("/daily", response_model=list[DailyStat])
async def daily_stats(
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rounds played per day, with unique players and mode/category breakdown."""
    since = datetime.utcnow() - timedelta(days=days)

    sessions = (
        (await db.execute(select(GameSession).where(GameSession.created_at >= since)))
        .scalars()
        .all()
    )

    players_by_session: dict[str, set[str]] = defaultdict(set)
    session_ids = [s.id for s in sessions]
    if session_ids:
        rows = (
            await db.execute(
                select(GamePlayerResult.session_id, GamePlayerResult.player_id).where(
                    GamePlayerResult.session_id.in_(session_ids)
                )
            )
        ).all()
        for session_id, player_id in rows:
            players_by_session[session_id].add(player_id)

    buckets: dict[str, dict] = {}
    for s in sessions:
        day = s.created_at.date().isoformat()
        bucket = buckets.setdefault(
            day,
            {
                "session_ids": set(),
                "player_ids": set(),
                "modes": Counter(),
                "categories": Counter(),
            },
        )
        bucket["session_ids"].add(s.id)
        bucket["player_ids"] |= players_by_session.get(s.id, set())
        bucket["modes"][s.mode] += 1
        bucket["categories"][s.category] += 1

    return [
        DailyStat(
            date=day,
            sessions=len(b["session_ids"]),
            unique_players=len(b["player_ids"]),
            by_mode=dict(b["modes"]),
            by_category=dict(b["categories"]),
        )
        for day, b in sorted(buckets.items())
    ]


@router.get("/sessions", response_model=list[SessionDetail])
async def recent_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Most recent rounds, with exactly what was shown to each player.

    Useful for reviewing whether the content being shown makes sense.
    """
    sessions = (
        (
            await db.execute(
                select(GameSession)
                .order_by(GameSession.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )

    results_by_session: dict[str, list[GamePlayerResult]] = defaultdict(list)
    session_ids = [s.id for s in sessions]
    if session_ids:
        results = (
            (
                await db.execute(
                    select(GamePlayerResult).where(GamePlayerResult.session_id.in_(session_ids))
                )
            )
            .scalars()
            .all()
        )
        for r in results:
            results_by_session[r.session_id].append(r)

    return [
        SessionDetail(
            id=s.id,
            created_at=s.created_at,
            mode=s.mode,
            category=s.category,
            difficulty=s.difficulty,
            n_impostors=s.n_impostors,
            players=[
                PlayerRoundOut(
                    player_name=r.player_name,
                    is_impostor=r.is_impostor,
                    word_shown=r.category_shown,
                )
                for r in results_by_session.get(s.id, [])
            ],
        )
        for s in sessions
    ]
