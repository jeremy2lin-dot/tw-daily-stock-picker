from __future__ import annotations

import html
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree


@dataclass(frozen=True)
class NewsCategory:
    name: str
    feeds: list[str]


@dataclass(frozen=True)
class NewsConfig:
    categories: list[NewsCategory]
    max_items_per_category: int = 3


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    source: str | None = None
    published_at: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class NewsSection:
    name: str
    items: list[NewsItem]
    errors: list[str]


def load_news_config(path: Path) -> NewsConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    max_items = int(data.get("max_items_per_category", 3))
    categories = [
        NewsCategory(name=str(category["name"]), feeds=[str(feed) for feed in category.get("feeds", [])])
        for category in data.get("categories", [])
    ]
    if not categories:
        raise ValueError(f"no news categories configured in {path}")
    return NewsConfig(categories=categories, max_items_per_category=max_items)


def collect_news(config: NewsConfig) -> list[NewsSection]:
    sections: list[NewsSection] = []
    for category in config.categories:
        items: list[NewsItem] = []
        errors: list[str] = []
        seen_titles: set[str] = set()
        feed_results: list[list[NewsItem]] = []
        for feed_url in category.feeds:
            try:
                feed_results.append(fetch_rss_items(feed_url))
            except RuntimeError as exc:
                errors.append(str(exc))
        max_feed_length = max((len(feed_items) for feed_items in feed_results), default=0)
        for item_index in range(max_feed_length):
            for feed_items in feed_results:
                if item_index >= len(feed_items):
                    continue
                item = feed_items[item_index]
                normalized_title = _normalize_title(item.title)
                if normalized_title in seen_titles:
                    continue
                seen_titles.add(normalized_title)
                items.append(item)
                if len(items) >= config.max_items_per_category:
                    break
            if len(items) >= config.max_items_per_category:
                break
        sections.append(NewsSection(name=category.name, items=items, errors=errors))
    return sections


def fetch_rss_items(feed_url: str) -> list[NewsItem]:
    request = Request(feed_url, headers={"User-Agent": "tw-daily-stock-picker/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"{feed_url}: HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"{feed_url}: {exc}") from exc

    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise RuntimeError(f"{feed_url}: invalid RSS XML") from exc

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    source_name = _feed_title(root)
    parsed_items: list[NewsItem] = []
    for item in items:
        parsed_item = _parse_item(item, source_name)
        if parsed_item is not None:
            parsed_items.append(parsed_item)
    return parsed_items


def build_news_message(report_date: date, sections: list[NewsSection], max_length: int = 3900) -> str:
    lines = [f"每日新聞更新 {report_date.isoformat()}"]
    for section in sections:
        lines.append("")
        lines.append(f"{section.name}")
        if section.items:
            for index, item in enumerate(section.items, start=1):
                source = f"｜{item.source}" if item.source else ""
                published = f"｜{item.published_at}" if item.published_at else ""
                lines.append(f"{index}. {item.title}{source}{published}")
                if item.summary:
                    lines.append(f"   {item.summary}")
                lines.append(f"   {item.link}")
        else:
            lines.append("暫時沒有取得新聞。")
        if section.errors:
            lines.append(f"來源讀取錯誤：{len(section.errors)} 個，請查看 GitHub Actions log。")

    message = "\n".join(lines)
    if len(message) <= max_length:
        return message
    return message[: max_length - 20].rstrip() + "\n...內容已截短"


def _parse_item(item: ElementTree.Element, feed_source: str | None = None) -> NewsItem | None:
    title = _find_text(item, "title")
    link = _find_link(item)
    if not title or not link:
        return None

    return NewsItem(
        title=html.unescape(title.strip()),
        link=link.strip(),
        source=_find_text(item, "source") or feed_source,
        published_at=_format_pub_date(_find_text(item, "pubDate") or _find_text(item, "updated")),
        summary=_clean_summary(_find_text(item, "description") or _find_text(item, "summary")),
    )


def _find_text(item: ElementTree.Element, tag: str) -> str | None:
    found = item.find(tag)
    if found is None:
        found = item.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    if found is None or found.text is None:
        return None
    return found.text.strip()


def _feed_title(root: ElementTree.Element) -> str | None:
    channel_title = root.find("./channel/title")
    if channel_title is not None and channel_title.text:
        return channel_title.text.strip()
    return _find_text(root, "title")


def _find_link(item: ElementTree.Element) -> str | None:
    rss_link = _find_text(item, "link")
    if rss_link:
        return rss_link
    atom_link = item.find("{http://www.w3.org/2005/Atom}link")
    if atom_link is not None:
        href = atom_link.attrib.get("href")
        if href:
            return href
    return None


def _format_pub_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).strftime("%m/%d %H:%M")
    except (TypeError, ValueError):
        return value[:16]


def _clean_summary(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"<[^>]+>", "", html.unescape(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None
    return cleaned[:110] + ("..." if len(cleaned) > 110 else "")


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().casefold()
