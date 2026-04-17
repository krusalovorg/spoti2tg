"""
Пример: только чтение «что играет» из Windows, без Telegram.
Дальше можно подключить любой транспорт (aiogram, HTTP, лог в файл).
"""

from __future__ import annotations

import time
from typing import Optional

from spoti2tg import PlaybackSource, TrackInfo, WindowsMediaClient


def format_line(track: TrackInfo) -> str:
    return f"{track.artists_text} — {track.title} [{track.status_text}]"


def main() -> None:
    source: PlaybackSource = WindowsMediaClient(source_app_filter="spotify")
    last: Optional[str] = None

    while True:
        track = source.get_current_track()
        line = format_line(track) if track else "(тишина)"
        if line != last:
            print(line)
            last = line
        time.sleep(3)


if __name__ == "__main__":
    main()
