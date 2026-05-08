from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .strategy import Pick


def write_picks_csv(picks: list[Pick], output_dir: Path, report_date: date) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{report_date.isoformat()}_picks.csv"

    with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "symbol",
                "name",
                "market",
                "close",
                "ma5",
                "ma20",
                "ma60",
                "rsi14",
                "volume",
                "avg_volume20",
                "volume_ratio",
                "high20",
                "limit_up_ratio",
                "net_income_after_tax",
                "roe",
                "eps",
                "per",
                "pbr",
                "bvp",
                "fiscal_date",
                "price_date",
                "score",
                "reasons",
            ]
        )
        for index, pick in enumerate(picks, start=1):
            writer.writerow(
                [
                    index,
                    pick.symbol,
                    pick.name,
                    pick.market,
                    f"{pick.close:.2f}",
                    f"{pick.ma5:.2f}",
                    f"{pick.ma20:.2f}",
                    f"{pick.ma60:.2f}",
                    f"{pick.rsi14:.2f}",
                    pick.volume,
                    f"{pick.avg_volume20:.0f}",
                    f"{pick.volume_ratio:.2f}",
                    f"{pick.high20:.2f}",
                    f"{pick.limit_up_ratio * 100:.2f}%",
                    f"{pick.net_income_after_tax:.0f}",
                    f"{pick.roe:.2f}%",
                    _format_optional(pick.eps),
                    _format_optional(pick.per),
                    _format_optional(pick.pbr),
                    _format_optional(pick.bvp),
                    pick.fiscal_date,
                    pick.price_date,
                    f"{pick.score:.2f}",
                    " | ".join(pick.reasons),
                ]
            )

    return report_path


def _format_optional(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"
