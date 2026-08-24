"""zuaef-telegram: outbound Telegram reporting for a composed ZUAEF Agent."""

from __future__ import annotations

from .client import TelegramClient, TelegramError
from .plugin import create_plugin

__all__ = ["TelegramClient", "TelegramError", "create_plugin"]
__version__ = "0.1.0"
