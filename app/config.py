import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./impostor.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

DEFAULT_CATEGORIES = [
    "animal", "país", "fruta", "profesión", "marca de ropa",
    "comida colombiana", "ciudad de Colombia", "superhéroe",
    "empresa de tecnología", "marca de carros", "jugador de fútbol famoso",
]
