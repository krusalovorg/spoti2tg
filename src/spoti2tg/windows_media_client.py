from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Optional

from .exceptions import WindowsMediaError
from .models import TrackInfo

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as SessionManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
    from winsdk.windows.storage.streams import DataReader
except ImportError:  # pragma: no cover - platform-specific import
    SessionManager = None  # type: ignore[assignment]
    PlaybackStatus = None  # type: ignore[assignment]
    DataReader = None  # type: ignore[assignment]


def _timedelta_to_ms(value: Optional[timedelta]) -> Optional[int]:
    if value is None:
        return None
    return int(value.total_seconds() * 1000)


class WindowsMediaClient:
    """
    Реализация :class:`~spoti2tg.playback.PlaybackSource` через Windows SMTC / GSMTC (``winsdk``).

    Можно использовать отдельно от Telegram — только для чтения «что сейчас играет».
    """

    def __init__(self, *, source_app_filter: Optional[str] = "spotify") -> None:
        self._source_app_filter = (source_app_filter or "").strip().lower()

    def get_current_track(self) -> Optional[TrackInfo]:
        if SessionManager is None:
            raise WindowsMediaError(
                "winsdk is not installed. Install dependencies: pip install -e ."
            )
        return self._run_async(self._get_current_track_async())

    async def _get_current_track_async(self) -> Optional[TrackInfo]:
        manager = await SessionManager.request_async()
        sessions = manager.get_sessions()
        if not sessions:
            return None

        selected = None
        for session in sessions:
            source_id = (session.source_app_user_model_id or "").lower()
            if self._source_app_filter and self._source_app_filter not in source_id:
                continue
            selected = session
            break

        if selected is None:
            selected = manager.get_current_session()
            if selected is None:
                return None

        props = await selected.try_get_media_properties_async()
        if not props or not props.title:
            return None

        timeline = selected.get_timeline_properties()
        playback_info = selected.get_playback_info()
        status = playback_info.playback_status
        is_playing = bool(
            PlaybackStatus is not None and status == PlaybackStatus.PLAYING
        )

        duration_ms = None
        progress_ms = None
        if timeline is not None:
            duration_ms = _timedelta_to_ms(timeline.end_time - timeline.start_time)
            progress_ms = _timedelta_to_ms(timeline.position)

        artists = []
        if props.artist:
            artists = [item.strip() for item in props.artist.split(",") if item.strip()]
        cover_image_bytes = await self._read_thumbnail_bytes(props.thumbnail)

        return TrackInfo(
            track_id=None,
            title=props.title,
            artists=artists or ["Unknown artist"],
            album=props.album_title or "Unknown album",
            track_url=None,
            image_url=None,
            cover_image_bytes=cover_image_bytes,
            is_playing=is_playing,
            progress_ms=progress_ms,
            duration_ms=duration_ms,
        )

    async def _read_thumbnail_bytes(self, thumbnail_ref) -> Optional[bytes]:
        if thumbnail_ref is None or DataReader is None:
            return None
        try:
            stream = await thumbnail_ref.open_read_async()
            size = int(stream.size)
            if size <= 0:
                return None
            reader = DataReader(stream)
            await reader.load_async(size)
            buffer = reader.read_buffer(size)
            return bytes(buffer)
        except Exception:
            return None

    @staticmethod
    def _run_async(coro):
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
