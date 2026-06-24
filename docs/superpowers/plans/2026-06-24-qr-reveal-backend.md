# El Impostor — QR Reveal System: Backend Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add permanent player tokens, game session persistence, and a public `/p/{token}` reveal endpoint to the FastAPI backend so the frontend can show each player their role via QR code without Telegram.

**Architecture:** Two new DB tables (`game_sessions`, `game_player_results`) track each game's outcome per player. Each `Player` row gets a permanent `token` UUID. `GET /p/{token}` is a public endpoint that returns the latest game state for that player. `telegram_id` becomes optional — Telegram send is best-effort and skipped when None.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, asyncpg, Alembic, Python 3.11+.

**Run all commands from:** `/Users/marco/Desktop/programming/github/impostor-api`

**Dependency:** Must be deployed before the frontend plan is executed.

**Scope note:** QR reveal only works for authenticated players stored in DB (have real `id` and `token`). The game engine skips `GamePlayerResult` rows when `player.id` is empty (anonymous players). The frontend wizard must require login before play.

---

### Task 1: Make `telegram_id` nullable and add `token` to Player

**Files:**
- Modify: `app/models_db.py`
- Modify: `app/models.py`
- Create: `alembic/versions/<hash>_player_token_nullable_telegram.py` (generated)

- [ ] **Step 1: Update SQLAlchemy Player model**

In `app/models_db.py`, replace the `Player` class with:

```python
class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False, default=_new_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="players")
```

- [ ] **Step 2: Update Pydantic Player model**

In `app/models.py`, change:
```python
class Player(BaseModel):
    name: str
    telegram_id: int
```
To:
```python
class Player(BaseModel):
    name: str
    telegram_id: int | None = None
```

- [ ] **Step 3: Generate Alembic migration**

```bash
DATABASE_URL="postgresql+asyncpg://impostor:impostor@localhost:5432/impostor" \
  alembic revision --autogenerate -m "player_token_nullable_telegram"
```

If running against Railway Postgres directly (no local DB), write the migration manually instead. Create `alembic/versions/<timestamp>_player_token_nullable_telegram.py`:

```python
"""player_token_nullable_telegram

Revision ID: <leave as generated>
Revises: c24b8d2842c1
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa
import uuid


def upgrade() -> None:
    # Make telegram_id nullable
    op.alter_column("players", "telegram_id", existing_type=sa.BigInteger(), nullable=True)
    # Add token column with unique constraint
    op.add_column("players", sa.Column("token", sa.String(), nullable=True))
    # Populate existing rows
    op.execute(
        "UPDATE players SET token = gen_random_uuid()::text WHERE token IS NULL"
    )
    op.alter_column("players", "token", nullable=False)
    op.create_unique_constraint("uq_players_token", "players", ["token"])


def downgrade() -> None:
    op.drop_constraint("uq_players_token", "players", type_="unique")
    op.drop_column("players", "token")
    op.alter_column("players", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
```

- [ ] **Step 4: Commit**

```bash
git add app/models_db.py app/models.py alembic/versions/
git commit -m "feat: player token + optional telegram_id"
```

---

### Task 2: Add GameSession and GamePlayerResult models

**Files:**
- Modify: `app/models_db.py`
- Create: `alembic/versions/<hash>_game_sessions.py` (generated)

- [ ] **Step 1: Add new models to `app/models_db.py`**

Add these two classes after the `Player` class (keep all existing imports; add `Boolean` to SQLAlchemy imports):

```python
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
```

Then add:

```python
class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    n_impostors: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    results: Mapped[list["GamePlayerResult"]] = relationship(
        "GamePlayerResult", back_populates="session", cascade="all, delete-orphan"
    )


class GamePlayerResult(Base):
    __tablename__ = "game_player_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[str] = mapped_column(
        String, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    is_impostor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    category_shown: Mapped[str] = mapped_column(String, nullable=False)

    session: Mapped["GameSession"] = relationship("GameSession", back_populates="results")
```

- [ ] **Step 2: Write migration manually**

Create `alembic/versions/<timestamp>_game_sessions.py`:

```python
"""game_sessions

Revision ID: <leave as generated>
Revises: <previous revision id>
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("n_impostors", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "game_player_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("is_impostor", sa.Boolean(), nullable=False),
        sa.Column("category_shown", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("game_player_results")
    op.drop_table("game_sessions")
```

- [ ] **Step 3: Commit**

```bash
git add app/models_db.py alembic/versions/
git commit -m "feat: game_sessions and game_player_results models"
```

---

### Task 3: Update users route for optional telegram_id + expose token

**Files:**
- Modify: `app/routes/users.py`

- [ ] **Step 1: Update PlayerCreate and PlayerOut**

Replace `PlayerCreate` and `PlayerOut` in `app/routes/users.py`:

```python
class PlayerCreate(BaseModel):
    name: str
    telegram_id: int | None = None


class PlayerOut(BaseModel):
    id: str
    name: str
    telegram_id: int | None
    token: str
```

- [ ] **Step 2: Update `create_player` to not pass `telegram_id` if None**

Replace the `create_player` function:

```python
@router.post("/players", response_model=PlayerOut, status_code=201)
async def create_player(
    body: PlayerCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    player = Player(
        id=_new_uuid(),
        user_id=user_id,
        name=body.name,
        telegram_id=body.telegram_id,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return PlayerOut(id=player.id, name=player.name, telegram_id=player.telegram_id, token=player.token)
```

- [ ] **Step 3: Update `list_players` response**

Replace the `list_players` function:

```python
@router.get("/players", response_model=list[PlayerOut])
async def list_players(
    user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Player).where(Player.user_id == user_id))
    return [
        PlayerOut(id=p.id, name=p.name, telegram_id=p.telegram_id, token=p.token)
        for p in result.scalars()
    ]
```

- [ ] **Step 4: Verify tests pass**

```bash
cd /Users/marco/Desktop/programming/github/impostor-api
pytest tests/ -v 2>/dev/null || echo "no tests yet"
```

- [ ] **Step 5: Commit**

```bash
git add app/routes/users.py
git commit -m "feat: users route — optional telegram_id, expose token"
```

---

### Task 4: Update game engine to persist sessions and handle None telegram_id

**Files:**
- Modify: `app/models.py`
- Modify: `app/game/engine.py`
- Modify: `app/routes/game.py`

- [ ] **Step 1: Add new response types to `app/models.py`**

Add these two classes at the bottom of `app/models.py`:

```python
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
```

Remove the old `StartGameResponse` that only had `category, mode, n_impostors, sent, failed`.

- [ ] **Step 2: Update `Player` model to carry `id` and `token`**

The Pydantic `Player` model is built from the DB player when the game starts. Update it to carry the DB fields the engine needs:

```python
class Player(BaseModel):
    id: str = ""          # DB player id (empty for anonymous/localStorage players)
    name: str
    telegram_id: int | None = None
    token: str = ""       # DB player token (empty for anonymous players)
```

- [ ] **Step 3: Update `StartGameRequest` to pass player tokens from frontend**

In `app/models.py`, update `StartGameRequest`:

```python
class StartGameRequest(BaseModel):
    players: list[Player]
    mode: Mode = Mode.caos
    difficulty: Difficulty = Difficulty.dificil
    categories: list[str] | None = None
    user_id: str | None = None  # injected by route from JWT, not from body
```

- [ ] **Step 4: Update `app/routes/game.py` to inject user_id and pass DB to engine**

Replace `app/routes/game.py` entirely:

```python
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
```

- [ ] **Step 5: Update `app/game/engine.py` to persist session and handle None telegram_id**

Replace `app/game/engine.py` entirely:

```python
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import _new_uuid
from app.game.roles import RoleAssignment, assign_roles
from app.models import Difficulty, Mode, Player, PlayerTokenOut, StartGameResponse
from app.models_db import GamePlayerResult, GameSession
from app.providers.llm import LLMProvider
from app.providers.messaging import MessagingProvider


def _build_message(assignment: RoleAssignment, mode: Mode, category: str, n_impostors: int) -> str:
    if not assignment.is_impostor:
        return f"🎯 *Categoría:* {category}\n🔤 *Tu palabra:* {assignment.word.upper()}"

    lines = [f"🎭 *¡Eres el IMPOSTOR!*\n\n📂 {category} — [{assignment.hint}]"]

    if mode == Mode.aliados and assignment.accomplice:
        lines.append(f"🤝 *Tu cómplice:* {assignment.accomplice}")

    if mode == Mode.espejo:
        lines.append(f"🪞 *Tu palabra (diferente):* {assignment.word.upper()}")

    if mode != Mode.ciego:
        lines.append(f"👥 *Impostores en juego:* {n_impostors}")

    return "\n".join(lines)


class GameEngine:
    def __init__(self, llm: LLMProvider, messaging: MessagingProvider, db: AsyncSession):
        self._llm = llm
        self._messaging = messaging
        self._db = db

    async def run(
        self,
        players: list[Player],
        categories: list[str],
        mode: Mode = Mode.caos,
        difficulty: Difficulty = Difficulty.dificil,
        user_id: str = "",
    ) -> StartGameResponse:
        category = random.choice(categories)
        word = await self._llm.pick_word(category)

        assignments = await assign_roles(
            players=players,
            mode=mode,
            category=category,
            word=word,
            difficulty=difficulty.value,
            llm=self._llm,
        )

        n_impostors = sum(1 for a in assignments if a.is_impostor)
        sent: list[str] = []
        failed: list[str] = []

        # Send Telegram messages (best-effort, skipped if no telegram_id)
        for assignment in assignments:
            if assignment.player.telegram_id is None:
                failed.append(assignment.player.name)
                continue
            msg = _build_message(assignment, mode, category, n_impostors)
            ok = await self._messaging.send(assignment.player.telegram_id, msg)
            (sent if ok else failed).append(assignment.player.name)
            status = "✓" if ok else "✗"
            role = "IMPOSTOR" if assignment.is_impostor else "jugador"
            print(f"  {status} {assignment.player.name} ({role})")

        # Persist game session + per-player results
        session = GameSession(
            id=_new_uuid(),
            user_id=user_id or "anonymous",
            category=category,
            mode=mode.value,
            difficulty=difficulty.value,
            n_impostors=n_impostors,
        )
        self._db.add(session)

        player_tokens: list[PlayerTokenOut] = []
        for assignment in assignments:
            # category_shown is the actual word for normal players, None hint for impostors
            category_shown = assignment.word if not assignment.is_impostor else ""
            result = GamePlayerResult(
                id=_new_uuid(),
                session_id=session.id,
                player_id=assignment.player.id or _new_uuid(),
                player_name=assignment.player.name,
                is_impostor=assignment.is_impostor,
                category_shown=category_shown,
            )
            self._db.add(result)
            player_tokens.append(PlayerTokenOut(name=assignment.player.name, token=assignment.player.token))

        await self._db.commit()

        print(
            f"\nModo: {mode.value} | Categoría: {category} "
            f"| Palabra: {word} | Impostores: {n_impostors}"
        )

        return StartGameResponse(
            category=category,
            mode=mode,
            n_impostors=n_impostors,
            sent=sent,
            failed=failed,
            session_id=session.id,
            players=player_tokens,
        )
```

- [ ] **Step 6: Commit**

```bash
git add app/models.py app/game/engine.py app/routes/game.py
git commit -m "feat: engine persists game session, handles optional telegram_id"
```

---

### Task 5: Create public GET /p/{token} reveal endpoint

**Files:**
- Create: `app/routes/reveal.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create `app/routes/reveal.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db import get_db
from app.models_db import GamePlayerResult, GameSession, Player

router = APIRouter()


class RevealStateOut(BaseModel):
    state: str  # "waiting" | "ready"
    player_name: str
    session_id: str | None = None
    is_impostor: bool | None = None
    category: str | None = None


@router.get("/p/{token}", response_model=RevealStateOut)
async def get_reveal_state(token: str, db: AsyncSession = Depends(get_db)):
    # Find player by token
    result = await db.execute(select(Player).where(Player.token == token))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Token not found")

    # Find the most recent game result for this player
    stmt = (
        select(GamePlayerResult, GameSession)
        .join(GameSession, GamePlayerResult.session_id == GameSession.id)
        .where(GamePlayerResult.player_id == player.id)
        .order_by(GameSession.created_at.desc())
        .limit(1)
    )
    row = await db.execute(stmt)
    pair = row.first()

    if pair is None:
        return RevealStateOut(state="waiting", player_name=player.name)

    game_result, session = pair
    return RevealStateOut(
        state="ready",
        player_name=player.name,
        session_id=session.id,
        is_impostor=game_result.is_impostor,
        category=game_result.category_shown if not game_result.is_impostor else None,
    )
```

- [ ] **Step 2: Register router in `app/main.py`**

Add after the existing router imports:

```python
from app.routes.reveal import router as reveal_router  # noqa: E402
```

And after the other `app.include_router` calls:

```python
app.include_router(reveal_router)
```

- [ ] **Step 3: Write a smoke test**

Create `tests/test_reveal.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_reveal_unknown_token_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/p/nonexistent-token-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 4: Run tests**

```bash
pip install pytest pytest-asyncio httpx
pytest tests/test_reveal.py -v
```

Expected output:
```
tests/test_reveal.py::test_reveal_unknown_token_returns_404 PASSED
tests/test_reveal.py::test_health PASSED
```

- [ ] **Step 5: Commit**

```bash
git add app/routes/reveal.py app/main.py tests/test_reveal.py
git commit -m "feat: GET /p/{token} public reveal endpoint"
```

---

### Task 6: Run Alembic migrations against Railway Postgres

**Context:** Alembic needs a sync DATABASE_URL (not asyncpg) to run migrations. Railway Postgres URL is in `.env`.

- [ ] **Step 1: Check alembic.ini has correct sqlalchemy.url**

The `alembic.ini` should read the URL from env. Verify `alembic/env.py` uses the DATABASE_URL from config. If it uses a hardcoded `alembic.ini` URL, update `alembic/env.py`'s `run_migrations_online` to pull from environment:

```python
import os
from sqlalchemy import create_engine

def run_migrations_online() -> None:
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

- [ ] **Step 2: Run migrations**

```bash
# Load .env vars first
export $(grep -v '^#' .env | xargs)
# Run migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade c24b8d2842c1 -> <hash1>, player_token_nullable_telegram
INFO  [alembic.runtime.migration] Running upgrade <hash1> -> <hash2>, game_sessions
```

- [ ] **Step 3: Redeploy to Railway**

```bash
cd /Users/marco/Desktop/programming/github/impostor-api
railway up --service impostor-api
```

Wait ~60s then verify:

```bash
curl https://impostor-api-production-09a1.up.railway.app/api/health
# Expected: {"status":"ok"}

curl https://impostor-api-production-09a1.up.railway.app/p/bogus-token
# Expected: {"detail":"Token not found"} with 404
```

- [ ] **Step 4: Final commit**

```bash
git add alembic/env.py
git commit -m "fix: alembic env uses DATABASE_URL from environment"
```
