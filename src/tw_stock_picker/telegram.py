from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


def send_message(config: TelegramConfig, message: str) -> None:
    payload = urlencode({"chat_id": config.chat_id, "text": message})
    _post_form(config.bot_token, "sendMessage", payload.encode("utf-8"))


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
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"failed to call Telegram {method}: HTTP {exc.code} {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"failed to call Telegram {method}: {exc}") from exc
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {payload}")

