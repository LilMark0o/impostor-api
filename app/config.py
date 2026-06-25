import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")


def _make_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./impostor.db")
    # Railway Postgres injects postgres:// or postgresql:// — convert to asyncpg driver
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = _make_database_url()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

DEFAULT_CATEGORIES = [
    "animal", "país", "fruta", "profesión", "marca de ropa",
    "comida colombiana", "ciudad de Colombia", "superhéroe",
    "empresa de tecnología", "marca de carros", "jugador de fútbol famoso",
]
