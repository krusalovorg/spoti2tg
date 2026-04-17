from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TrackInfo:
    track_id: Optional[str]
    title: str
    artists: list[str]
    album: str
    track_url: Optional[str]
    image_url: Optional[str]
    cover_image_bytes: Optional[bytes]
    is_playing: bool
    progress_ms: Optional[int]
    duration_ms: Optional[int]

    @property
    def artists_text(self) -> str:
        return ", ".join(self.artists)

    @property
    def status_text(self) -> str:
        return "Играет" if self.is_playing else "Пауза"


@dataclass(frozen=True)
class TelegramMessageRef:
    chat_id: str
    message_id: int
