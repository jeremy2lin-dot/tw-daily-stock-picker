from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Stock:
    symbol: str
    name: str
    market: str

    @property
    def yahoo_symbol(self) -> str:
        suffix = "TWO" if self.market.upper() == "TWO" else "TW"
        return f"{self.symbol}.{suffix}"


@dataclass(frozen=True)
class DailyBar:
    timestamp: int
    close: float
    volume: int


@dataclass(frozen=True)
class Fundamentals:
    fiscal_date: str
    price_date: str
    net_income_after_tax: float
    roe: float
    eps: float | None
    per: float | None
    pbr: float | None
    bvp: float | None


class PriceClient(Protocol):
    def history(self, stock: Stock, lookback_days: int) -> list[DailyBar]:
        ...


class FundamentalClient(Protocol):
    def fundamentals(self, stock: Stock, close: float) -> Fundamentals:
        ...


def load_watchlist(path: Path) -> list[Stock]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"symbol", "name", "market"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"Watchlist must include columns: {', '.join(sorted(required))}")
        return [
            Stock(
                symbol=row["symbol"].strip(),
                name=row["name"].strip(),
                market=row["market"].strip().upper(),
            )
            for row in reader
            if row.get("symbol", "").strip()
        ]


class YahooChartClient:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    def history(self, stock: Stock, lookback_days: int) -> list[DailyBar]:
        period2 = int(time.time())
        period1 = period2 - lookback_days * 24 * 60 * 60
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{stock.yahoo_symbol}"
            f"?period1={period1}&period2={period2}&interval=1d&events=history"
        )
        request = Request(url, headers={"User-Agent": "tw-daily-stock-picker/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"failed to fetch Yahoo chart data: {exc}") from exc

        result = payload.get("chart", {}).get("result")
        if not result:
            error = payload.get("chart", {}).get("error")
            raise RuntimeError(f"no chart data returned: {error}")

        chart = result[0]
        timestamps = chart.get("timestamp") or []
        quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        bars: list[DailyBar] = []
        for timestamp, close, volume in zip(timestamps, closes, volumes):
            if close is None or volume is None:
                continue
            bars.append(DailyBar(timestamp=int(timestamp), close=float(close), volume=int(volume)))
        return bars


class FinMindClient:
    base_url = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    def fundamentals(self, stock: Stock, close: float) -> Fundamentals:
        start_date = (date.today() - timedelta(days=550)).isoformat()
        statement_rows = self._fetch("TaiwanStockFinancialStatements", stock.symbol, start_date)
        balance_rows = self._fetch("TaiwanStockBalanceSheet", stock.symbol, start_date)
        per_rows = self._fetch("TaiwanStockPER", stock.symbol, (date.today() - timedelta(days=45)).isoformat())

        latest_statement = _latest_by_date(statement_rows)
        latest_balance = _latest_by_date(balance_rows)
        latest_previous_balance = _previous_by_date(balance_rows, latest_balance["date"])
        latest_per = _latest_by_date(per_rows)

        statement_values = _values_by_type(statement_rows, latest_statement["date"])
        balance_values = _values_by_type(balance_rows, latest_balance["date"])
        previous_balance_values = _values_by_type(balance_rows, latest_previous_balance["date"]) if latest_previous_balance else {}

        net_income = _first_number(
            statement_values,
            ["IncomeAfterTaxes", "IncomeAfterTax", "IncomeFromContinuingOperations"],
        )
        equity = _first_number(balance_values, ["EquityAttributableToOwnersOfParent", "Equity"])
        previous_equity = (
            _first_number(previous_balance_values, ["EquityAttributableToOwnersOfParent", "Equity"])
            if previous_balance_values
            else None
        )
        average_equity = (equity + previous_equity) / 2 if previous_equity else equity
        roe = (net_income / average_equity) * 4 * 100 if average_equity else 0

        per = _optional_number(latest_per, "PER")
        pbr = _optional_number(latest_per, "PBR")
        eps = (close / per) if per and per > 0 else _optional_number(statement_values, "EPS")
        bvp = (close / pbr) if pbr and pbr > 0 else None

        return Fundamentals(
            fiscal_date=str(latest_statement["date"]),
            price_date=str(latest_per.get("date", "")),
            net_income_after_tax=net_income,
            roe=roe,
            eps=eps,
            per=per,
            pbr=pbr,
            bvp=bvp,
        )

    def _fetch(self, dataset: str, stock_id: str, start_date: str) -> list[dict]:
        query = urlencode({"dataset": dataset, "data_id": stock_id, "start_date": start_date})
        request = Request(f"{self.base_url}?{query}", headers={"User-Agent": "tw-daily-stock-picker/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"failed to fetch FinMind {dataset}: {exc}") from exc

        if payload.get("status") != 200:
            raise RuntimeError(f"FinMind {dataset} returned status {payload.get('status')}: {payload.get('msg')}")
        rows = payload.get("data") or []
        if not rows:
            raise RuntimeError(f"FinMind {dataset} returned no rows")
        return rows


def _latest_by_date(rows: list[dict]) -> dict:
    return max(rows, key=lambda row: str(row.get("date", "")))


def _previous_by_date(rows: list[dict], latest_date: str) -> dict | None:
    previous_dates = sorted({str(row.get("date", "")) for row in rows if str(row.get("date", "")) < latest_date})
    if not previous_dates:
        return None
    previous_date = previous_dates[-1]
    for row in rows:
        if str(row.get("date", "")) == previous_date:
            return row
    return None


def _values_by_type(rows: list[dict], row_date: str) -> dict[str, float]:
    return {
        str(row.get("type")): float(row["value"])
        for row in rows
        if str(row.get("date")) == row_date and row.get("value") not in (None, "")
    }


def _required_number(values: dict, key: str) -> float:
    value = _optional_number(values, key)
    if value is None:
        raise RuntimeError(f"missing required field: {key}")
    return value


def _optional_number(values: dict, key: str) -> float | None:
    value = values.get(key)
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_number(values: dict[str, float], keys: list[str]) -> float:
    for key in keys:
        value = _optional_number(values, key)
        if value is not None:
            return value
    raise RuntimeError(f"missing required field, expected one of: {', '.join(keys)}")
