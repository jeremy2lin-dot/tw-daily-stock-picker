from __future__ import annotations


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def average_int(values: list[int], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None

    changes = [current - previous for previous, current in zip(values, values[1:])]
    recent = changes[-period:]
    gains = [change for change in recent if change > 0]
    losses = [-change for change in recent if change < 0]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0

    relative_strength = avg_gain / avg_loss
    return 100 - (100 / (1 + relative_strength))


def highest(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return max(values[-period:])
