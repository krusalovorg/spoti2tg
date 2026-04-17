from __future__ import annotations

import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.exceptions import AiogramError, TelegramBadRequest
from aiogram.types import BufferedInputFile, InputMediaPhoto, LinkPreviewOptions

from .exceptions import TelegramAPIError
from .models import TelegramMessageRef


class TelegramClient:
    def __init__(
        self,
        bot_token: str,
        *,
        api_base: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._start_background_loop,
            name="spoti2tg-telegram-loop",
            daemon=True,
        )
        self._thread.start()
        session = self._build_session(api_base=api_base, proxy=proxy)
        self._bot = Bot(
            token=bot_token,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = False,
    ) -> TelegramMessageRef:
        result = self._run(
            self._bot.send_message(
                chat_id=chat_id,
                text=text,
                link_preview_options=LinkPreviewOptions(
                    is_disabled=disable_web_page_preview
                ),
            )
        )
        return TelegramMessageRef(
            chat_id=str(result.chat.id),
            message_id=int(result.message_id),
        )

    def edit_message_text(
        self,
        *,
        chat_id: str,
        message_id: int,
        text: str,
        disable_web_page_preview: bool = False,
    ) -> None:
        try:
            self._run(
                self._bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    link_preview_options=LinkPreviewOptions(
                        is_disabled=disable_web_page_preview
                    ),
                )
            )
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            raise TelegramAPIError(f"Telegram edit failed: {exc}") from exc
        except AiogramError as exc:
            raise TelegramAPIError(f"Telegram edit failed: {exc}") from exc

    def edit_message_media(
        self,
        *,
        chat_id: str,
        message_id: int,
        media: bytes,
        filename: str = "cover.jpg",
        caption: Optional[str] = None,
    ) -> None:
        try:
            self._run(
                self._bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaPhoto(
                        media=BufferedInputFile(media, filename=filename),
                        caption=caption or "",
                        parse_mode=ParseMode.HTML,
                    ),
                )
            )
        except AiogramError as exc:
            raise TelegramAPIError(f"Telegram media edit failed: {exc}") from exc

    def send_photo(
        self,
        *,
        chat_id: str,
        photo: bytes,
        caption: str,
        filename: str = "cover.jpg",
    ) -> TelegramMessageRef:
        try:
            result = self._run(
                self._bot.send_photo(
                    chat_id=chat_id,
                    photo=BufferedInputFile(photo, filename=filename),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            )
            return TelegramMessageRef(
                chat_id=str(result.chat.id),
                message_id=int(result.message_id),
            )
        except AiogramError as exc:
            raise TelegramAPIError(f"Telegram send photo failed: {exc}") from exc

    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=30)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TelegramAPIError("Telegram API call timed out") from exc

    @staticmethod
    def _build_session(
        *,
        api_base: Optional[str],
        proxy: Optional[str],
    ) -> AiohttpSession:
        kwargs = {}
        if proxy:
            kwargs["proxy"] = proxy
        if api_base:
            kwargs["api"] = TelegramAPIServer.from_base(api_base)
        return AiohttpSession(**kwargs)

    def _start_background_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
