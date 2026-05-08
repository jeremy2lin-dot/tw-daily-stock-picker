from __future__ import annotations

from tw_stock_picker.data import DailyBar, Fundamentals, Stock
from tw_stock_picker.strategy import Strategy, evaluate_stock


def make_strategy() -> Strategy:
    return Strategy(
        lookback_days=100,
        min_history_days=70,
        min_price=0,
        min_avg_volume=0,
        min_volume_ratio=0,
        max_rsi14=101,
        require_ma_alignment=False,
        require_price_above_ma20=False,
        require_20_day_breakout=False,
        require_limit_up=True,
        limit_up_threshold=0.095,
        min_net_income_after_tax=0,
        min_roe=15,
        top_n=20,
    )


def make_fundamentals(net_income: float = 1_000_000, roe: float = 18) -> Fundamentals:
    return Fundamentals(
        fiscal_date="2025-12-31",
        price_date="2026-05-06",
        net_income_after_tax=net_income,
        roe=roe,
        eps=5.1,
        per=12.3,
        pbr=2.1,
        bvp=29.9,
    )


def make_limit_up_bars() -> list[DailyBar]:
    closes = [50 + index * 0.1 for index in range(78)] + [60, 66]
    volumes = [2_000 for _ in range(79)] + [8_000]
    return [
        DailyBar(timestamp=index, close=close, volume=volume)
        for index, (close, volume) in enumerate(zip(closes, volumes))
    ]


def test_evaluate_stock_returns_pick_for_limit_up_and_fundamentals() -> None:
    pick = evaluate_stock(Stock("2330", "TSMC", "TW"), make_limit_up_bars(), make_strategy(), make_fundamentals())

    assert pick is not None
    assert pick.symbol == "2330"
    assert pick.limit_up_ratio >= 0.095
    assert pick.net_income_after_tax > 0
    assert pick.roe > 15
    assert pick.eps == 5.1


def test_evaluate_stock_rejects_non_limit_up() -> None:
    bars = make_limit_up_bars()
    bars[-1] = DailyBar(timestamp=bars[-1].timestamp, close=62, volume=bars[-1].volume)

    pick = evaluate_stock(Stock("2330", "TSMC", "TW"), bars, make_strategy(), make_fundamentals())

    assert pick is None


def test_evaluate_stock_rejects_low_roe() -> None:
    pick = evaluate_stock(Stock("2330", "TSMC", "TW"), make_limit_up_bars(), make_strategy(), make_fundamentals(roe=10))

    assert pick is None
