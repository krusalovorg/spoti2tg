# spoti2tg

Python-библиотека для публикации текущего трека в Telegram с обновлением одного сообщения (через `editMessageText`), а не отправкой нового поста при каждой смене трека.

## Возможности

- Режим без Spotify токена: чтение трека из Windows media session
- Попытка прикрепить обложку трека из Windows media session (если доступна)
- Отправка первого сообщения в Telegram
- Редактирование существующего сообщения при смене трека/статуса
- Настраиваемая реакция на состояние "ничего не играет"
- Конфиг из `.env` и/или аргументов конструктора

## Установка

```bash
pip install -e .
```

## Уровни API (для разработчиков)

### 1) Только «что играет» (Windows SDK)

Единый контракт — ``PlaybackSource``: метод ``get_current_track()`` возвращает ``TrackInfo`` или ``None``.

- ``WindowsMediaClient`` — реализация через SMTC / ``winsdk`` (Windows).
- ``fetch_windows_now_playing(...)`` — одноразовое чтение без хранения клиента.

Пример:

```python
from typing import Optional

from spoti2tg import TrackInfo, WindowsMediaClient

source = WindowsMediaClient(source_app_filter="spotify")
track: Optional[TrackInfo] = source.get_current_track()
```

См. также ``examples/playback_only.py``.

### 2) Свой источник + готовый постинг в Telegram

Реализуйте ``PlaybackSource`` (любой класс с ``get_current_track``) и передайте в постер:

```python
from typing import Optional

from spoti2tg import NowPlayingPoster, PlaybackSource, TrackInfo

class MySource:
    def get_current_track(self) -> Optional[TrackInfo]:
        ...

NowPlayingPoster(playback=MySource(), telegram_bot_token="...", telegram_chat_id="...").run()
```

### 3) Нижний уровень: свой Telegram

- ``TelegramClient`` — обёртка над ``aiogram`` (send / edit).
- ``NowPlayingTracker`` — логика опроса и троттлинга; принимает любой ``PlaybackSource`` и ``TelegramClient``.

## Быстрый старт

```python
from spoti2tg import NowPlayingPoster

poster = NowPlayingPoster(
    telegram_bot_token="...",
    telegram_chat_id="...",
    windows_source_app="spotify",
)
poster.run()
```

## Конфигурация

Поддерживаемые параметры:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_API_BASE` (опционально, кастомный Bot API endpoint)
- `TELEGRAM_PROXY` (опционально, прокси URL для aiogram, например `http://user:pass@host:port`)
- `WINDOWS_SOURCE_APP` (подстрока фильтра источника, по умолчанию `spotify`)
- `WINDOWS_POLL_INTERVAL` (как часто опрашивать Windows media session, по умолчанию `3` секунды)
- `POLL_INTERVAL` (минимальный интервал между обновлениями Telegram при изменении только прогресса, по умолчанию `30` секунд)
- `SHOW_NOT_PLAYING`
- `MESSAGE_TEMPLATE`

Приоритет: аргументы конструктора выше значений из `.env`.

Пример `.env` есть в `.env.example`.

## Шаблон сообщения

По умолчанию:

```text
🎶 <b>Сейчас играет</b>

<b>{title}</b>
👤 <i>{artists}</i>
💿 <i>{album}</i>

────────────
▶️ <b>{status}</b> · {progress_bar}
<code>⏱ {progress} · {duration}</code>
{url}
```

Доступные плейсхолдеры:

- `{title}`
- `{artists}`
- `{album}`
- `{url}`
- `{status}`
- `{progress_bar}`
- `{progress}`
- `{duration}`

## Структура пакета

- `spoti2tg/config.py` — загрузка/валидация конфигурации
- `spoti2tg/models.py` — модели данных
- `spoti2tg/playback.py` — протокол ``PlaybackSource`` и утилита ``fetch_windows_now_playing``
- `spoti2tg/windows_media_client.py` — чтение трека из Windows media session
- `spoti2tg/telegram_client.py` — интеграция с Telegram Bot API
- `spoti2tg/tracker.py` — сервис polling + логика отправки/редактирования
- `spoti2tg/poster.py` — публичный facade API (`NowPlayingPoster`)
- `spoti2tg/exceptions.py` — custom exceptions

## Примечания

- Работа идёт без Spotify API токена через системные медиа-сессии Windows.
- Опрос Windows: каждые `WINDOWS_POLL_INTERVAL` секунд (по умолчанию `3`) — быстро ловим смену трека.
- Обновление Telegram: при смене трека или паузы/воспроизведения — сразу; при том же треке и изменении только прогресса/бара — не чаще чем раз в `POLL_INTERVAL` секунд (по умолчанию `30`).
- Если `api.telegram.org` нестабилен у провайдера в РФ, задайте `TELEGRAM_API_BASE` (свой reverse proxy/self-hosted Bot API) или `TELEGRAM_PROXY`.
- `message_id` хранится в памяти процесса. Если нужен persistence между рестартами, можно добавить storage-адаптер (JSON/SQLite/Redis).
