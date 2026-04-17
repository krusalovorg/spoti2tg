from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from dotenv import load_dotenv

from .exceptions import ConfigError

DEFAULT_MESSAGE_TEMPLATE = (
    "🎶 <b>Сейчас играет</b>\n"
    "\n"
    "<b>{title}</b>\n"
    "👤 <i>{artists}</i>\n"
    "💿 <i>{album}</i>\n"
    "\n"
    "────────────\n"
    "▶️ <b>{status}</b> · {progress_bar}\n"
    "<code>⏱ {progress} · {duration}</code>\n"
    "{url}"
)


def _as_bool(value: Optional[str], *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _as_float(value: Optional[str], *, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid float value: {value}") from exc


def _normalize_template(value: str) -> str:
    return value.replace("\\n", "\n")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_api_base: Optional[str] = None
    telegram_proxy: Optional[str] = None
    windows_source_app: str = "spotify"
    windows_poll_interval: float = 3.0
    poll_interval: float = 30.0
    show_not_playing: bool = True
    message_template: str = DEFAULT_MESSAGE_TEMPLATE

    @classmethod
    def from_sources(cls, **kwargs: Any) -> "Settings":
        load_dotenv()

        values = {
            "telegram_bot_token": kwargs.get("telegram_bot_token")
            or kwargs.get("TELEGRAM_BOT_TOKEN")
            or os.getenv("TELEGRAM_BOT_TOKEN"),
            "telegram_chat_id": kwargs.get("telegram_chat_id")
            or kwargs.get("TELEGRAM_CHAT_ID")
            or os.getenv("TELEGRAM_CHAT_ID"),
            "telegram_api_base": kwargs.get("telegram_api_base")
            or kwargs.get("TELEGRAM_API_BASE")
            or os.getenv("TELEGRAM_API_BASE"),
            "telegram_proxy": kwargs.get("telegram_proxy")
            or kwargs.get("TELEGRAM_PROXY")
            or os.getenv("TELEGRAM_PROXY"),
            "windows_source_app": kwargs.get("windows_source_app")
            or kwargs.get("WINDOWS_SOURCE_APP")
            or os.getenv("WINDOWS_SOURCE_APP")
            or "spotify",
            "windows_poll_interval": kwargs.get("windows_poll_interval")
            or kwargs.get("WINDOWS_POLL_INTERVAL")
            or os.getenv("WINDOWS_POLL_INTERVAL"),
            "poll_interval": kwargs.get("poll_interval")
            or kwargs.get("POLL_INTERVAL")
            or os.getenv("POLL_INTERVAL"),
            "show_not_playing": kwargs.get("show_not_playing")
            if kwargs.get("show_not_playing") is not None
            else kwargs.get("SHOW_NOT_PLAYING")
            or os.getenv("SHOW_NOT_PLAYING"),
            "message_template": kwargs.get("message_template")
            or kwargs.get("MESSAGE_TEMPLATE")
            or os.getenv("MESSAGE_TEMPLATE"),
        }

        if not values["telegram_bot_token"]:
            raise ConfigError("TELEGRAM_BOT_TOKEN is required")
        if not values["telegram_chat_id"]:
            raise ConfigError("TELEGRAM_CHAT_ID is required")

        poll_interval = (
            values["poll_interval"]
            if isinstance(values["poll_interval"], (float, int))
            else _as_float(values["poll_interval"], default=30.0)
        )
        windows_poll_interval = (
            values["windows_poll_interval"]
            if isinstance(values["windows_poll_interval"], (float, int))
            else _as_float(values["windows_poll_interval"], default=3.0)
        )
        show_not_playing = (
            values["show_not_playing"]
            if isinstance(values["show_not_playing"], bool)
            else _as_bool(values["show_not_playing"], default=True)
        )

        return cls(
            telegram_bot_token=str(values["telegram_bot_token"]),
            telegram_chat_id=str(values["telegram_chat_id"]),
            telegram_api_base=(
                str(values["telegram_api_base"])
                if values["telegram_api_base"] is not None
                else None
            ),
            telegram_proxy=(
                str(values["telegram_proxy"])
                if values["telegram_proxy"] is not None
                else None
            ),
            windows_source_app=str(values["windows_source_app"]),
            windows_poll_interval=max(0.5, float(windows_poll_interval)),
            poll_interval=float(poll_interval),
            show_not_playing=show_not_playing,
            message_template=(
                _normalize_template(str(values["message_template"]))
                if values["message_template"] is not None
                else DEFAULT_MESSAGE_TEMPLATE
            ),
        )
