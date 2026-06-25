import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base, _new_uuid
from app.models_db import Player, User


@pytest.fixture
async def mem_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def test_create_user(mem_engine):
    session_factory = async_sessionmaker(mem_engine, expire_on_commit=False)
    async with session_factory() as s:
        user = User(id=_new_uuid(), google_id="g-1", email="a@b.com", name="Alice")
        s.add(user)
        await s.commit()
        await s.refresh(user)
    assert user.id is not None
    assert user.lang == "es"


async def test_create_player(mem_engine):
    from sqlalchemy import select
    session_factory = async_sessionmaker(mem_engine, expire_on_commit=False)
    async with session_factory() as s:
        user = User(id=_new_uuid(), google_id="g-2", email="b@b.com", name="Bob")
        s.add(user)
        await s.commit()
        # Player with user_id (logged-in)
        player = Player(id=_new_uuid(), user_id=user.id, name="Bob P", telegram_id=111)
        s.add(player)
        # Anonymous player (no user_id)
        anon = Player(id=_new_uuid(), user_id=None, name="Anon", telegram_id=None)
        s.add(anon)
        await s.commit()
        result = await s.execute(select(Player).where(Player.user_id == user.id))
        assert result.scalar_one_or_none() is not None
        result2 = await s.execute(select(Player).where(Player.user_id.is_(None)))
        assert result2.scalar_one_or_none() is not None
