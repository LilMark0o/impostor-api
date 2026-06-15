from telegram import Bot

from app.config import TELEGRAM_TOKEN


class TelegramProvider:
    def __init__(self):
        self._bot = Bot(token=TELEGRAM_TOKEN)

    async def send(self, chat_id: int, text: str) -> bool:
        try:
            await self._bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            return True
        except Exception as e:
            print(f"  Error enviando a {chat_id}: {e}")
            return False
