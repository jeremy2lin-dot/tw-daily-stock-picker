# 每日新聞 Telegram 推送

這個專案用 GitHub Actions 每天早上自動抓取新聞 RSS，並透過 Telegram 傳送標題與連結。

## 每日排程

- 台北時間：每天 08:00
- UTC：每天 00:00
- Workflow：[daily-news.yml](.github/workflows/daily-news.yml)
- 新聞來源設定：[news_feeds.toml](config/news_feeds.toml)

目前新聞分類：

- 國際：最近 10 則
- 財經：最近 10 則

訊息格式只包含新聞標題與連結。

## Telegram 設定

GitHub Repository 需要設定兩個 Actions Secrets：

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

設定位置：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

## 本機測試

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
tw-daily-news
```

測試 Telegram 發送：

```powershell
$env:TELEGRAM_BOT_TOKEN = "你的 BOT TOKEN"
$env:TELEGRAM_CHAT_ID = "你的 CHAT ID"
tw-daily-news --telegram
```
