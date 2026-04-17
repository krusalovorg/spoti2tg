from __future__ import annotations

from typing import Any, Optional

from .config import Settings
from .models import TrackInfo
from .playback import PlaybackSource
from .telegram_client import TelegramClient
from .tracker import NowPlayingTracker
from .windows_media_client import WindowsMediaClient


class NowPlayingPoster:
    def __init__(
        self,
        *,
        playback: Optional[PlaybackSource] = None,
        **kwargs: Any,
    ) -> None:
        self.settings = Settings.from_sources(**kwargs)

        self.source_client: PlaybackSource = playback or WindowsMediaClient(
            source_app_filter=self.settings.windows_source_app
        )

        self.telegram_client = TelegramClient(
            self.settings.telegram_bot_token,
            api_base=self.settings.telegram_api_base,
            proxy=self.settings.telegram_proxy,
        )
        self.tracker = NowPlayingTracker(
            settings=self.settings,
            source_client=self.source_client,
            telegram_client=self.telegram_client,
        )

    def run(self) -> None:
        self.tracker.run_forever()

    def tick(self) -> Optional[TrackInfo]:
        return self.tracker.tick()
