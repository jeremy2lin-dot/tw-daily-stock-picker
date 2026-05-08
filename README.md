# 台股每日自動選股

這個專案用 GitHub Actions 在台股收盤後自動執行選股，並透過 Telegram 傳送結果。

> 這是研究與自動化工具，不是投資建議。實際交易前請自行確認資料、流動性、風險與交易成本。

## 每日排程

GitHub Actions 設定在：

- 台北時間：每週一至週五 16:00
- UTC：每週一至週五 08:00
- Workflow：[daily-stock-picker.yml](.github/workflows/daily-stock-picker.yml)

程式會在執行時檢查：

- 週六、週日不執行
- `config/twse_holidays_2026.csv` 內的台股休市日不執行
- 休市日也會傳 Telegram 訊息告知「今日不執行」

## 選股條件

目前預設條件在 [strategy.toml](config/strategy.toml)：

```toml
require_limit_up = true
limit_up_threshold = 0.095
min_net_income_after_tax = 0
min_roe = 15
```

意思是：

- 每日漲停近似股：收盤價相對前一交易日收盤價漲幅至少 9.5%
- 最新一季稅後淨利大於 0
- 最新一季年化 ROE 大於 15%

報表會列出：

- EPS
- PER
- PBR
- BVP
- 稅後淨利
- ROE
- 財報日期
- 估值日期

## Telegram 設定

1. 在 Telegram 找 `@BotFather` 建立 Bot。
2. 記下 Bot Token。
3. 對你的 Bot 傳一則訊息。
4. 取得你的 Chat ID，可用：

```text
https://api.telegram.org/bot<你的BOT_TOKEN>/getUpdates
```

到 GitHub Repository 設定：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

新增兩個 Secret：

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 發佈到 GitHub

把整個專案推到 GitHub 後，GitHub Actions 會自動使用：

```yaml
on:
  schedule:
    - cron: "0 8 * * 1-5"
  workflow_dispatch:
```

也可以在 GitHub Actions 頁面手動按 `Run workflow` 測試。

## 股票清單

編輯 [watchlist.csv](config/watchlist.csv)：

```csv
symbol,name,market
2330,台積電,TW
6488,環球晶,TWO
```

`market` 可填：

- `TW`: 上市，查詢 `2330.TW`
- `TWO`: 上櫃，查詢 `6488.TWO`

## 本機測試

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
tw-stock-picker --skip-non-trading-day
```

測試 Telegram：

```powershell
$env:TELEGRAM_BOT_TOKEN = "你的 BOT TOKEN"
$env:TELEGRAM_CHAT_ID = "你的 CHAT ID"
tw-stock-picker --skip-non-trading-day --telegram --send-report-file
```

## 休市日維護

目前已放入 2026 年台股市場休市日：[twse_holidays_2026.csv](config/twse_holidays_2026.csv)。

每年證交所公布下一年度市場開休市日期後，新增或更新同格式 CSV 即可。資料來源建議以 [TWSE 市場開休市日期](https://www.twse.com.tw/holidaySchedule/holidaySchedule?response=html) 為準。
