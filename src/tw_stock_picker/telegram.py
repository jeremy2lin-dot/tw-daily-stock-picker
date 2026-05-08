from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .strategy import Pick


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


def build_message(report_date: str, picks: list[Pick], errors: dict[str, str], skipped_reason: str | None = None) -> str:
    if skipped_reason:
        return f"台股每日自動選股 {report_date}\n今日不執行：{skipped_reason}"

    lines = [
        f"台股每日自動選股 {report_date}",
        f"符合條件：{len(picks)} 檔",
        "條件：漲停、稅後淨利 > 0、ROE > 15%",
    ]

    if picks:
        lines.append("")
        for index, pick in enumerate(picks[:10], start=1):
            lines.append(
                f"{index}. {pick.symbol} {pick.name} "
                f"收盤 {pick.close:.2f} 漲幅 {pick.limit_up_ratio * 100:.2f}% "
                f"ROE {pick.roe:.2f}% EPS {_fmt(pick.eps)} "
                f"PER {_fmt(pick.per)} PBR {_fmt(pick.pbr)} BVP {_fmt(pick.bvp)}"
            )
    else:
        lines.append("")
        lines.append("今日沒有符合條件的股票。")

    if errors:
        lines.append("")
        lines.append(f"資料錯誤：{len(errors)} 檔，請查看 GitHub Actions log。")

    return "\n".join(lines)


def send_message(config: TelegramConfig, message: str) -> None:
    payload = urlencode({"chat_id": config.chat_id, "text": message})
    _post_form(config.bot_token, "sendMessage", payload.encode("utf-8"))


def send_document(config: TelegramConfig, document_path: Path, caption: str) -> None:
    boundary = "----tw-stock-picker-boundary"
    file_bytes = document_path.read_bytes()
    parts = [
        _form_field(boundary, "chat_id", config.chat_id),
        _form_field(boundary, "caption", caption),
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{document_path.name}"\r\n'
            "Content-Type: text/csv\r\n\r\n"
        ).encode("utf-8")
        + file_bytes
        + b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    _post_raw(config.bot_token, "sendDocument", body, f"multipart/form-data; boundary={boundary}")


def _post_form(bot_token: str, method: str, body: bytes) -> None:
    _post_raw(bot_token, method, body, "application/x-www-form-urlencoded")


def _post_raw(bot_token: str, method: str, body: bytes, content_type: str) -> None:
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=body,
        headers={"Content-Type": content_type, "User-Agent": "tw-daily-stock-picker/0.1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"failed to call Telegram {method}: {exc}") from exc
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {payload}")


def _form_field(boundary: str, name: str, value: str) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def _fmt(value: float | None) -> str:
    return "--" if value is None else f"{value:.2f}"
