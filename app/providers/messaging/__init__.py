from typing import Protocol, runtime_checkable

from app.config import TELEGRAM_TOKEN
from app.providers.messaging.telegram import TelegramProvider


@runtime_checkable
class MessagingProvider(Protocol):
    async def send(self, chat_id: int, text: str) -> bool: ...


class NoMessagingProvider:
    """Used when TELEGRAM_TOKEN is not configured.

    The single-device flow doesn't deliver words by message at all, so this
    simply reports "not sent" instead of crashing while building a Bot.
    """

    async def send(self, chat_id: int, text: str) -> bool:
        return False


def get_provider(name: str = "telegram") -> MessagingProvider:
    if name == "telegram":
        if not TELEGRAM_TOKEN:
            return NoMessagingProvider()
        return TelegramProvider()
    raise ValueError(f"Unknown messaging provider: {name}")
