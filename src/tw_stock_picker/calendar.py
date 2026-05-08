from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")


@dataclass(frozen=True)
class TradingDayStatus:
    is_trading_day: bool
    reason: str


def taipei_today() -> date:
    from datetime import datetime

    return datetime.now(TAIPEI_TZ).date()


def load_holidays(path: Path) -> dict[date, str]:
    if not path.exists():
        return {}

    holidays: dict[date, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_date = row.get("date", "").strip()
            if not raw_date:
                continue
            holidays[date.fromisoformat(raw_date)] = row.get("name", "").strip() or "market holiday"
    return holidays


def trading_day_status(day: date, holidays: dict[date, str]) -> TradingDayStatus:
    if day.weekday() >= 5:
        return TradingDayStatus(False, "weekend")
    if day in holidays:
        return TradingDayStatus(False, holidays[day])
    return TradingDayStatus(True, "trading day")
