from __future__ import annotations

from datetime import date

from tw_stock_picker.news import NewsItem, NewsSection, build_news_message


def test_build_news_message_groups_items_by_category() -> None:
    message = build_news_message(
        date(2026, 6, 14),
        [
            NewsSection(
                name="科技",
                items=[
                    NewsItem(
                        title="AI 晶片需求升溫",
                        link="https://example.com/ai-chip",
                        source="Example News",
                        published_at="06/14 08:00",
                        summary="供應鏈訂單增加。",
                    )
                ],
                errors=[],
            )
        ],
    )

    assert "每日新聞更新 2026-06-14" in message
    assert "科技" in message
    assert "AI 晶片需求升溫" in message
    assert "https://example.com/ai-chip" in message
    assert "Example News" not in message
    assert "06/14 08:00" not in message
    assert "供應鏈訂單增加。" not in message


def test_build_news_message_reports_empty_category() -> None:
    message = build_news_message(date(2026, 6, 14), [NewsSection(name="台灣", items=[], errors=[])])

    assert "台灣" in message
    assert "暫時沒有取得新聞。" in message
