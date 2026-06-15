import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

DEFAULT_CATEGORIES = [
    "animal",
    "país",
    "fruta",
    "profesión",
    "marca de ropa",
    "comida colombiana",
    "ciudad de Colombia",
    "superhéroe",
    "empresa de tecnología",
    "marca de carros",
    "jugador de fútbol famoso",
]
