from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .calendar import taipei_today
from .news import build_news_message, collect_news, load_news_config
from .settings import telegram_config_from_env
from .telegram import send_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily Taiwan news Telegram sender")
    parser.add_argument("--config", default="config/news_feeds.toml", help="Path to news feed TOML")
    parser.add_argument("--as-of", default=None, help="News date in YYYY-MM-DD; defaults to today in Asia/Taipei")
    parser.add_argument("--telegram", action="store_true", help="Send Telegram message using TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report_date = date.fromisoformat(args.as_of) if args.as_of else taipei_today()
    config = load_news_config(Path(args.config))
    sections = collect_news(config)
    message = build_news_message(report_date, sections)

    print(message)
    if args.telegram:
        send_message(telegram_config_from_env(), message)


if __name__ == "__main__":
    main()
