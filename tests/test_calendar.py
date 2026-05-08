from __future__ import annotations

from datetime import date

from tw_stock_picker.calendar import trading_day_status


def test_trading_day_status_rejects_weekend() -> None:
    status = trading_day_status(date(2026, 5, 9), {})

    assert not status.is_trading_day
    assert status.reason == "weekend"


def test_trading_day_status_rejects_holiday() -> None:
    status = trading_day_status(date(2026, 5, 1), {date(2026, 5, 1): "Labor Day"})

    assert not status.is_trading_day
    assert status.reason == "Labor Day"


def test_trading_day_status_accepts_weekday() -> None:
    status = trading_day_status(date(2026, 5, 7), {})

    assert status.is_trading_day
