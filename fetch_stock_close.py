#!/usr/bin/env python3
"""
台股每日收盤價抓取腳本
- 從 holdings.txt 讀取持股清單（新增/刪除持股只需改這個檔案）
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
HOLDINGS_PATH = "holdings.txt"   # 持股清單
OUTPUT_PATH   = "stock_prices.txt"  # 收盤價輸出

# Discord Webhook 從環境變數讀取（存在 GitHub Secrets）
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
# ────────────────────────────────────────────────────────


def load_holdings():
    """
    從 holdings.txt 讀取持股清單
    格式每行：股票名稱,ticker
    例如：聯發科,2454.TW
    """
    if not os.path.exists(HOLDINGS_PATH):
        print(f"❌ 找不到 {HOLDINGS_PATH}")
        return {}

    holdings = {}
    with open(HOLDINGS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) == 2:
                name, ticker = parts[0].strip(), parts[1].strip()
                holdings[name] = ticker

    return holdings


def send_discord(message):
    """發送 Discord 通知"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 未設定，跳過通知")
        return
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


def fetch_prices(ticker_map):
    """抓取所有持倉的收盤價"""
    tickers = list(ticker_map.values())
    data = yf.download(tickers, period="2d", progress=False, auto_adjust=True)

    success = {}
    failed  = []

    for name, ticker in ticker_map.items():
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

    ticker_map = load_holdings()
    if not ticker_map:
        send_discord("❌ 台股收盤價更新失敗\n找不到持股清單 holdings.txt")
        exit(1)

    print(f"\n📋 持股清單（{len(ticker_map)} 支）：{list(ticker_map.keys())}")
    print(f"\n📡 抓取收盤價...")

    prices, failed = fetch_prices(ticker_map)

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
