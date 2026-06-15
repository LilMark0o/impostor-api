from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.routes.game import router as game_router  # noqa: E402

app = FastAPI(title="Impostor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
