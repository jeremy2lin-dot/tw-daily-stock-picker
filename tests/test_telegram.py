from __future__ import annotations

from tw_stock_picker.telegram import build_message


def test_build_message_for_skipped_day() -> None:
    message = build_message("2026-05-01", [], {}, skipped_reason="Labor Day")

    assert "今日不執行" in message
    assert "Labor Day" in message
