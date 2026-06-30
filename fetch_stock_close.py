#!/usr/bin/env python3
"""
台股每日收盤價抓取腳本
- 持股清單直接從 TICKER_MAP 讀取（GitHub Actions 環境）
- 抓取當日收盤價
- 存成 stock_prices.txt，commit 回 GitHub repo
- 透過 Discord Webhook 通知成功與否
"""

import yfinance as yf
from datetime import date
import os
import urllib.request
import urllib.error
import json

# ── 設定區 ──────────────────────────────────────────────
OUTPUT_PATH = "stock_prices.txt"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1520449880307273821/CBrShP4nh2532BizcMLxkaC1_9tRPUKdMNInmwiR1k4Dme8gks4U-mlK0I7z8mmZ1QDV"

# 股票名稱 → Yahoo Finance ticker 對照表
# ⚠️ 新增或賣出持股時，手動更新這裡
TICKER_MAP = {
    "群創":          "3481.TW",
    "頎邦":          "6147.TWO",
    "聯發科":        "2454.TW",
    "愛普":          "6531.TW",
    "新日興":        "3376.TW",
    "采鈺":          "6789.TW",
    "鈦昇":          "8027.TWO",
    "華通":          "2313.TW",
    "昇達科":        "3491.TWO",
    "兆赫":          "2485.TW",
    "鼎元":          "2426.TW",
    "光寶科":        "2301.TW",
    "創惟":          "6104.TWO",
    "智原":          "3035.TW",
    "嘉澤":          "3533.TW",
    "祥碩":          "5269.TW",
    "正達":          "3149.TW",
    "元大台灣50正2": "00631L.TW",
}
# ────────────────────────────────────────────────────────


def send_discord(message):
    """發送 Discord 通知"""
    try:
        payload = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("Discord 通知成功")
    except urllib.error.HTTPError as e:
        print(f"Discord 通知失敗：HTTP {e.code} — {e.read().decode()}")
    except Exception as e:
        print(f"Discord 通知失敗：{e}")


def fetch_prices():
    """抓取所有持倉的收盤價"""
    tickers = list(TICKER_MAP.values())
    data = yf.download(tickers, period="2d", progress=False, auto_adjust=True)

    success = {}
    failed  = []

    for name, ticker in TICKER_MAP.items():
        try:
            series = data["Close"] if len(tickers) == 1 else data["Close"][ticker]
            close  = round(float(series.dropna().iloc[-1]), 2)
            success[name] = close
            print(f"  ✅ {name:12s} {close}")
        except Exception as e:
            failed.append(name)
            print(f"  ❌ {name:12s} 失敗：{e}")

    return success, failed


def save_txt(prices):
    """將收盤價存成 txt 檔"""
    today = date.today().strftime("%Y-%m-%d")
    lines = [today]
    for name, price in prices.items():
        lines.append(f"{name},{price}")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n✅ 已儲存 → {OUTPUT_PATH}")


if __name__ == "__main__":
    today = date.today().strftime("%Y-%m-%d")
    print("=" * 45)
    print(f"  台股收盤價抓取  {today}")
    print("=" * 45)
    print(f"\n📡 抓取 {len(TICKER_MAP)} 支股票收盤價...")

    prices, failed = fetch_prices()
    if prices:
        save_txt(prices)

    # Discord 通知
    lines = [f"@here 📈 **台股收盤價更新** {today}"]
    lines.append(f"✅ 成功：{len(prices)} 支　❌ 失敗：{len(failed)} 支")
    if failed:
        lines.append(f"失敗清單：{', '.join(failed)}")
    lines.append("```")
    for name, price in prices.items():
        lines.append(f"{name:12s} {price}")
    lines.append("```")

    send_discord("\n".join(lines))
