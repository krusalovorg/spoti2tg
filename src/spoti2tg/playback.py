from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from .models import TrackInfo


@runtime_checkable
class PlaybackSource(Protocol):
    """Источник данных о текущем воспроизведении (единый контракт для своих интеграций)."""

    def get_current_track(self) -> Optional[TrackInfo]:
        """Текущий трек или ``None``, если ничего не играет / нет сессии."""
        ...


def fetch_windows_now_playing(
    *,
    source_app_filter: str = "spotify",
) -> Optional[TrackInfo]:
    """
    Одноразово прочитать состояние из Windows media session (удобно для скриптов и своих ботов).

    Для цикла опроса лучше создать один экземпляр :class:`~spoti2tg.WindowsMediaClient`.
    """
    from .windows_media_client import WindowsMediaClient

    return WindowsMediaClient(source_app_filter=source_app_filter).get_current_track()
