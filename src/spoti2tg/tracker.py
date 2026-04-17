from __future__ import annotations

import html
import logging
import time
from typing import Optional

from .config import Settings
from .exceptions import Spoti2TGError
from .models import TelegramMessageRef, TrackInfo
from .playback import PlaybackSource
from .telegram_client import TelegramClient

logger = logging.getLogger(__name__)


def _format_ms(value: Optional[int]) -> str:
    if value is None:
        return "--:--"
    total_seconds = max(0, value // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _build_progress_bar(
    progress_ms: Optional[int],
    duration_ms: Optional[int],
    *,
    length: int = 14,
) -> str:
    if not progress_ms or not duration_ms or duration_ms <= 0:
        return f"[{'-' * length}]"
    ratio = max(0.0, min(1.0, progress_ms / duration_ms))
    filled = int(round(ratio * length))
    return f"[{'=' * filled}{'-' * (length - filled)}]"


def _track_identity(track: Optional[TrackInfo]) -> str:
    if track is None:
        return "__idle__"
    return "\x00".join(
        [
            track.title,
            track.artists_text,
            track.album,
            "1" if track.is_playing else "0",
        ]
    )


class NowPlayingTracker:
    def __init__(
        self,
        settings: Settings,
        source_client: PlaybackSource,
        telegram_client: TelegramClient,
    ) -> None:
        self._settings = settings
        self._source = source_client
        self._telegram = telegram_client
        self._message_ref: Optional[TelegramMessageRef] = None
        self._last_sent_identity: Optional[str] = None
        self._last_sent_text: Optional[str] = None
        self._last_telegram_edit_monotonic: float = 0.0

    def run_forever(self) -> None:
        win_iv = self._settings.windows_poll_interval
        tg_iv = max(1.0, float(self._settings.poll_interval))
        logger.info(
            "NowPlayingTracker started: windows_poll=%ss, telegram_progress=%ss, show_not_playing=%s",
            win_iv,
            tg_iv,
            self._settings.show_not_playing,
        )
        while True:
            try:
                self.tick()
            except Spoti2TGError as exc:
                logger.error("Tracker iteration failed: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive log
                logger.exception("Unexpected tracker error: %s", exc)
            time.sleep(max(0.5, float(self._settings.windows_poll_interval)))

    def tick(self) -> Optional[TrackInfo]:
        track = self._source.get_current_track()
        identity = _track_identity(track)

        if identity != self._last_sent_identity:
            if track is None:
                logger.info("No active track in Windows media session")
            else:
                logger.info(
                    "Track changed: %s — %s (%s)",
                    track.artists_text,
                    track.title,
                    track.status_text,
                )
        else:
            logger.debug(
                "Windows poll: %s",
                "idle" if track is None else f"{track.artists_text} — {track.title}",
            )

        text = self._build_message(track)
        if text is None:
            logger.debug("No-op: show_not_playing is disabled")
            return track

        telegram_interval = max(1.0, float(self._settings.poll_interval))
        now = time.monotonic()

        if self._message_ref is None:
            logger.info("Sending initial Telegram message")
            self._push_telegram(track, text)
            self._last_sent_identity = identity
            self._last_sent_text = text
            self._last_telegram_edit_monotonic = now
            return track

        if identity != self._last_sent_identity:
            logger.info("Updating Telegram (track or playback state changed)")
            self._push_telegram(track, text)
            self._last_sent_identity = identity
            self._last_sent_text = text
            self._last_telegram_edit_monotonic = now
            return track

        if text == self._last_sent_text:
            logger.debug("No-op: rendered message unchanged")
            return track

        if now - self._last_telegram_edit_monotonic >= telegram_interval:
            logger.info("Updating Telegram (progress, throttled interval elapsed)")
            self._push_telegram(track, text)
            self._last_sent_text = text
            self._last_telegram_edit_monotonic = now
        else:
            logger.debug(
                "Telegram progress update skipped (next edit in %.1fs)",
                telegram_interval - (now - self._last_telegram_edit_monotonic),
            )

        return track

    def _push_telegram(self, track: Optional[TrackInfo], text: str) -> None:
        if self._message_ref is None:
            if track and track.cover_image_bytes:
                self._message_ref = self._telegram.send_photo(
                    chat_id=self._settings.telegram_chat_id,
                    photo=track.cover_image_bytes,
                    caption=text,
                )
            else:
                self._message_ref = self._telegram.send_message(
                    chat_id=self._settings.telegram_chat_id,
                    text=text,
                    disable_web_page_preview=not bool(track and track.image_url),
                )
            logger.info(
                "Initial message sent: chat_id=%s, message_id=%s",
                self._message_ref.chat_id,
                self._message_ref.message_id,
            )
            return

        logger.info(
            "Editing Telegram message: chat_id=%s, message_id=%s",
            self._message_ref.chat_id,
            self._message_ref.message_id,
        )
        if track and track.cover_image_bytes:
            self._telegram.edit_message_media(
                chat_id=self._message_ref.chat_id,
                message_id=self._message_ref.message_id,
                media=track.cover_image_bytes,
                caption=text,
            )
        else:
            self._telegram.edit_message_text(
                chat_id=self._message_ref.chat_id,
                message_id=self._message_ref.message_id,
                text=text,
                disable_web_page_preview=not bool(track and track.image_url),
            )
        logger.info("Telegram message updated")

    def _build_message(self, track: Optional[TrackInfo]) -> Optional[str]:
        if track is None:
            if not self._settings.show_not_playing:
                return None
            return (
                "🔇 <b>Пауза</b>\n"
                "\n"
                "<i>Сейчас ничего не играет</i>"
            )

        template = self._settings.message_template
        message = template.format(
            title=html.escape(track.title),
            artists=html.escape(track.artists_text),
            album=html.escape(track.album),
            url=html.escape(track.track_url or ""),
            status=html.escape(track.status_text),
            progress=_format_ms(track.progress_ms),
            duration=_format_ms(track.duration_ms),
            progress_bar=_build_progress_bar(track.progress_ms, track.duration_ms),
        )
        return "\n".join(line.rstrip() for line in message.splitlines()).strip()
