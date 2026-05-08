from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .data import FundamentalClient, Fundamentals, PriceClient, Stock
from .indicators import average_int, highest, rsi, sma


@dataclass(frozen=True)
class Strategy:
    lookback_days: int
    min_history_days: int
    min_price: float
    min_avg_volume: float
    min_volume_ratio: float
    max_rsi14: float
    require_ma_alignment: bool
    require_price_above_ma20: bool
    require_20_day_breakout: bool
    require_limit_up: bool
    limit_up_threshold: float
    min_net_income_after_tax: float
    min_roe: float
    top_n: int


@dataclass(frozen=True)
class Pick:
    symbol: str
    name: str
    market: str
    close: float
    ma5: float
    ma20: float
    ma60: float
    rsi14: float
    volume: int
    avg_volume20: float
    volume_ratio: float
    high20: float
    limit_up_ratio: float
    net_income_after_tax: float
    roe: float
    eps: float | None
    per: float | None
    pbr: float | None
    bvp: float | None
    fiscal_date: str
    price_date: str
    score: float
    reasons: tuple[str, ...]


def load_strategy(path: Path) -> Strategy:
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    return Strategy(
        lookback_days=int(data.get("lookback_days", 180)),
        min_history_days=int(data.get("min_history_days", 70)),
        min_price=float(data.get("min_price", 20)),
        min_avg_volume=float(data.get("min_avg_volume", 1_000_000)),
        min_volume_ratio=float(data.get("min_volume_ratio", 1.2)),
        max_rsi14=float(data.get("max_rsi14", 75)),
        require_ma_alignment=bool(data.get("require_ma_alignment", True)),
        require_price_above_ma20=bool(data.get("require_price_above_ma20", True)),
        require_20_day_breakout=bool(data.get("require_20_day_breakout", True)),
        require_limit_up=bool(data.get("require_limit_up", False)),
        limit_up_threshold=float(data.get("limit_up_threshold", 0.095)),
        min_net_income_after_tax=float(data.get("min_net_income_after_tax", 0)),
        min_roe=float(data.get("min_roe", 0)),
        top_n=int(data.get("top_n", 20)),
    )


def screen_stocks(
    stocks: list[Stock],
    strategy: Strategy,
    client: PriceClient,
    fundamental_client: FundamentalClient | None = None,
) -> tuple[list[Pick], dict[str, str]]:
    picks: list[Pick] = []
    errors: dict[str, str] = {}

    for stock in stocks:
        try:
            bars = client.history(stock, strategy.lookback_days)
            close = bars[-1].close if bars else 0
            fundamentals = fundamental_client.fundamentals(stock, close) if fundamental_client else None
            pick = evaluate_stock(stock, bars, strategy, fundamentals)
        except Exception as exc:
            errors[stock.symbol] = str(exc)
            continue
        if pick:
            picks.append(pick)

    picks.sort(key=lambda item: item.score, reverse=True)
    return picks[: strategy.top_n], errors


def evaluate_stock(stock: Stock, bars, strategy: Strategy, fundamentals: Fundamentals | None = None) -> Pick | None:
    if len(bars) < strategy.min_history_days:
        return None

    closes = [bar.close for bar in bars]
    volumes = [bar.volume for bar in bars]
    close = closes[-1]
    previous_close = closes[-2]
    volume = volumes[-1]

    ma5 = sma(closes, 5)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    rsi14 = rsi(closes, 14)
    avg_volume20 = average_int(volumes, 20)
    high20 = highest(closes[:-1], 20)
    if None in (ma5, ma20, ma60, rsi14, avg_volume20, high20):
        return None

    assert ma5 is not None
    assert ma20 is not None
    assert ma60 is not None
    assert rsi14 is not None
    assert avg_volume20 is not None
    assert high20 is not None

    volume_ratio = volume / avg_volume20 if avg_volume20 else 0
    limit_up_ratio = (close / previous_close - 1) if previous_close else 0
    reasons: list[str] = []

    if strategy.require_limit_up and limit_up_ratio < strategy.limit_up_threshold:
        return None
    if limit_up_ratio >= strategy.limit_up_threshold:
        reasons.append(f"limit-up {limit_up_ratio * 100:.2f}%")

    if close < strategy.min_price:
        return None
    if avg_volume20 < strategy.min_avg_volume:
        return None
    if volume_ratio < strategy.min_volume_ratio:
        return None
    reasons.append(f"volume {volume_ratio:.2f}x")

    if rsi14 > strategy.max_rsi14:
        return None
    reasons.append(f"RSI14 {rsi14:.1f}")

    if strategy.require_ma_alignment and not (ma5 > ma20 > ma60):
        return None
    if ma5 > ma20 > ma60:
        reasons.append("MA5 > MA20 > MA60")

    if strategy.require_price_above_ma20 and close <= ma20:
        return None
    if close > ma20:
        reasons.append("close > MA20")

    breakout_ratio = close / high20 if high20 else 0
    if strategy.require_20_day_breakout and breakout_ratio < 1:
        return None
    if breakout_ratio >= 1:
        reasons.append("20-day breakout")

    if fundamentals:
        if fundamentals.net_income_after_tax <= strategy.min_net_income_after_tax:
            return None
        reasons.append(f"net income {fundamentals.net_income_after_tax:.0f}")

        if fundamentals.roe <= strategy.min_roe:
            return None
        reasons.append(f"ROE {fundamentals.roe:.2f}%")
    elif strategy.min_net_income_after_tax > 0 or strategy.min_roe > 0:
        return None

    score = (
        (close / ma20 - 1) * 100
        + (ma5 / ma20 - 1) * 80
        + min(volume_ratio, 3) * 10
        + max(0, 75 - rsi14) * 0.2
        + max(0, breakout_ratio - 1) * 120
        + ((fundamentals.roe - strategy.min_roe) if fundamentals else 0)
    )

    return Pick(
        symbol=stock.symbol,
        name=stock.name,
        market=stock.market,
        close=close,
        ma5=ma5,
        ma20=ma20,
        ma60=ma60,
        rsi14=rsi14,
        volume=volume,
        avg_volume20=avg_volume20,
        volume_ratio=volume_ratio,
        high20=high20,
        limit_up_ratio=limit_up_ratio,
        net_income_after_tax=fundamentals.net_income_after_tax if fundamentals else 0,
        roe=fundamentals.roe if fundamentals else 0,
        eps=fundamentals.eps if fundamentals else None,
        per=fundamentals.per if fundamentals else None,
        pbr=fundamentals.pbr if fundamentals else None,
        bvp=fundamentals.bvp if fundamentals else None,
        fiscal_date=fundamentals.fiscal_date if fundamentals else "",
        price_date=fundamentals.price_date if fundamentals else "",
        score=score,
        reasons=tuple(reasons),
    )
