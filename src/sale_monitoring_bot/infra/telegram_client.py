from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from beartype import beartype

from sale_monitoring_bot.config import Settings

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_MESSAGE_LENGTH = 4096


class TelegramClient:
    def __init__(self, settings: Settings) -> None:
        settings.require_telegram_runtime()
        assert settings.telegram_bot_token is not None
        assert settings.telegram_chat_id is not None
        self._token = settings.telegram_bot_token.get_secret_value()
        self._chat_id = settings.telegram_chat_id

    @beartype
    async def send_message(self, text: str) -> None:
        chunks = _split_message(text, _TELEGRAM_MAX_MESSAGE_LENGTH)
        async with Bot(token=self._token) as bot:
            for chunk in chunks:
                try:
                    await bot.send_message(chat_id=self._chat_id, text=chunk)
                except TelegramAPIError:
                    logger.exception("Ошибка отправки в Telegram")
                    raise


@beartype
def _split_message(text: str, max_length: int) -> list[str]:
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        line_len = len(line) + 1
        if line_len > max_length:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            chunks.extend(_split_long_line(line, max_length))
            continue
        if current_len + line_len > max_length:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))
    return chunks


@beartype
def _split_long_line(line: str, max_length: int) -> list[str]:
    return [line[i : i + max_length] for i in range(0, len(line), max_length)]
