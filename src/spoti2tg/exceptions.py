class Spoti2TGError(Exception):
    """Base library exception."""


class ConfigError(Spoti2TGError):
    """Raised when configuration is invalid or incomplete."""


class TelegramAPIError(Spoti2TGError):
    """Raised when Telegram Bot API request fails."""


class WindowsMediaError(Spoti2TGError):
    """Raised when Windows media session API is unavailable or fails."""
