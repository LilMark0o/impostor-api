from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.game import router as game_router  # noqa: E402
from app.routes.reveal import router as reveal_router  # noqa: E402
from app.routes.users import router as users_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Impostor API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router, prefix="/api")
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(reveal_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
