import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
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

CATEGORY_GROUPS: dict[str, list[str]] = {
    "⚽ Fútbol": [
        "jugador de fútbol famoso",
        "ganador del Balón de Oro",
        "club de fútbol europeo",
        "selección nacional de fútbol",
        "técnico de fútbol famoso",
        "estadio de fútbol famoso",
        "competición de fútbol",
        "posición en el campo de fútbol",
        "goleador histórico",
    ],
    "🌍 General": [
        "animal",
        "país",
        "fruta",
        "profesión",
        "superhéroe",
        "empresa de tecnología",
        "marca de carros",
        "comida colombiana",
        "ciudad de Colombia",
        "marca de ropa",
    ],
    "🎭 Cultura": [
        "película famosa",
        "serie de televisión",
        "artista de música latina",
        "videojuego famoso",
    ],
}

CATEGORY_PACKS: dict[str, dict] = {
    "balon_de_oro": {
        "label": "Balón de Oro",
        "emoji": "🏆",
        "categories": [
            "ganador del Balón de Oro",
            "club de fútbol europeo",
            "selección nacional de fútbol",
            "técnico de fútbol famoso",
            "estadio de fútbol famoso",
        ],
    },
    "futbol": {
        "label": "Fútbol completo",
        "emoji": "⚽",
        "categories": CATEGORY_GROUPS["⚽ Fútbol"],
    },
    "general": {
        "label": "Modo clásico",
        "emoji": "🎯",
        "categories": CATEGORY_GROUPS["🌍 General"],
    },
    "todo": {
        "label": "Todo mezclado",
        "emoji": "🎲",
        "categories": [cat for cats in CATEGORY_GROUPS.values() for cat in cats],
    },
}

DEFAULT_CATEGORIES = [cat for cats in CATEGORY_GROUPS.values() for cat in cats]
