from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .calendar import load_holidays, taipei_today, trading_day_status
from .data import FinMindClient, YahooChartClient, load_watchlist
from .report import write_picks_csv
from .strategy import load_strategy, screen_stocks
from .telegram import TelegramConfig, build_message, send_document, send_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily Taiwan stock picker")
    parser.add_argument("--watchlist", default="config/watchlist.csv", help="Path to stock watchlist CSV")
    parser.add_argument("--strategy", default="config/strategy.toml", help="Path to strategy TOML")
    parser.add_argument("--holidays", default="config/twse_holidays_2026.csv", help="Path to TWSE holiday CSV")
    parser.add_argument("--output-dir", default="reports", help="Directory for generated reports")
    parser.add_argument("--as-of", default=None, help="Report date in YYYY-MM-DD; defaults to today in Asia/Taipei")
    parser.add_argument("--skip-non-trading-day", action="store_true", help="Exit successfully on weekends or TWSE holidays")
    parser.add_argument("--telegram", action="store_true", help="Send Telegram message using TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    parser.add_argument("--send-report-file", action="store_true", help="Attach CSV report to Telegram message")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    watchlist_path = Path(args.watchlist)
    strategy_path = Path(args.strategy)
    holidays_path = Path(args.holidays)
    output_dir = Path(args.output_dir)
    report_date = date.fromisoformat(args.as_of) if args.as_of else taipei_today()

    telegram_config = _telegram_config() if args.telegram else None
    holidays = load_holidays(holidays_path)
    status = trading_day_status(report_date, holidays)
    if args.skip_non_trading_day and not status.is_trading_day:
        message = build_message(report_date.isoformat(), [], {}, skipped_reason=status.reason)
        print(message)
        if telegram_config:
            send_message(telegram_config, message)
        return

    stocks = load_watchlist(watchlist_path)
    strategy = load_strategy(strategy_path)
    client = YahooChartClient()
    fundamental_client = FinMindClient()

    picks, errors = screen_stocks(stocks, strategy, client, fundamental_client)
    report_path = write_picks_csv(picks, output_dir, report_date)
    message = build_message(report_date.isoformat(), picks, errors)

    print(f"Scanned: {len(stocks)}")
    print(f"Picks: {len(picks)}")
    print(f"Report: {report_path}")
    if errors:
        print("Data errors:")
        for symbol, error_message in errors.items():
            print(f"- {symbol}: {error_message}")
    if telegram_config:
        send_message(telegram_config, message)
        if args.send_report_file:
            send_document(telegram_config, report_path, f"{report_date.isoformat()} 台股選股報表")


def _telegram_config() -> TelegramConfig:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required when --telegram is used.", file=sys.stderr)
        raise SystemExit(2)
    return TelegramConfig(bot_token=bot_token, chat_id=chat_id)


if __name__ == "__main__":
    main()
