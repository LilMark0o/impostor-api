from typing import Protocol, runtime_checkable

from app.providers.messaging.telegram import TelegramProvider


@runtime_checkable
class MessagingProvider(Protocol):
    async def send(self, chat_id: int, text: str) -> bool: ...


def get_provider(name: str = "telegram") -> MessagingProvider:
    if name == "telegram":
        return TelegramProvider()
    raise ValueError(f"Unknown messaging provider: {name}")
