from __future__ import annotations

import os
import sys

from .telegram import TelegramConfig


def telegram_config_from_env() -> TelegramConfig:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required when Telegram is used.", file=sys.stderr)
        raise SystemExit(2)
    return TelegramConfig(bot_token=bot_token, chat_id=chat_id)
