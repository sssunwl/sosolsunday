import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}


def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
        timeout=10,
    )
    return resp.ok


def scrape_hk_express() -> list[str]:
    """HK Express 優惠頁面"""
    deals = []
    try:
        url = "https://www.hkexpress.com/en-hk/promotions/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 嘗試多種常見 class 結構
        items = (
            soup.select(".promotion-card")
            or soup.select("[class*='promo']")
            or soup.select("[class*='deal']")
            or soup.select("article")
        )

        for item in items[:6]:
            title = item.get_text(" ", strip=True)[:120]
            if len(title) > 10:
                deals.append(f"🟠 <b>HK Express</b>: {title}")

        if not deals:
            deals.append("🟠 HK Express: 目前無法解析優惠（頁面結構可能已更新）")
    except Exception as e:
        deals.append(f"🟠 HK Express 抓取失敗: {str(e)[:60]}")

    return deals


def scrape_cathay() -> list[str]:
    """國泰航空優惠頁面"""
    deals = []
    try:
        url = "https://www.cathaypacific.com/cx/en_HK/offers/flights.html"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items = (
            soup.select(".offer-card")
            or soup.select("[class*='offer']")
            or soup.select("[class*='promotion']")
            or soup.select("article")
        )

        for item in items[:6]:
            title = item.get_text(" ", strip=True)[:120]
            if len(title) > 10:
                deals.append(f"🟢 <b>國泰航空</b>: {title}")

        if not deals:
            deals.append("🟢 國泰: 目前無法解析優惠（頁面結構可能已更新）")
    except Exception as e:
        deals.append(f"🟢 國泰 抓取失敗: {str(e)[:60]}")

    return deals


def scrape_airasia() -> list[str]:
    """Air Asia 香港優惠頁面"""
    deals = []
    try:
        url = "https://www.airasia.com/en/flights-promotion?locale=zh-HK"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items = (
            soup.select("[class*='promo']")
            or soup.select("[class*='deal']")
            or soup.select("[class*='sale']")
            or soup.select("article")
        )

        for item in items[:6]:
            title = item.get_text(" ", strip=True)[:120]
            if len(title) > 10:
                deals.append(f"🔴 <b>Air Asia</b>: {title}")

        if not deals:
            deals.append("🔴 Air Asia: 目前無法解析優惠（頁面結構可能已更新）")
    except Exception as e:
        deals.append(f"🔴 Air Asia 抓取失敗: {str(e)[:60]}")

    return deals


def build_message(all_deals: list[str]) -> str:
    hkt_offset = 8 * 3600
    now_hkt = datetime.utcnow()
    now_str = now_hkt.strftime("%Y-%m-%d %H:%M") + " HKT"

    lines = [
        f"✈️ <b>香港出發航班優惠</b>",
        f"🕐 更新時間：{now_str}",
        "",
    ]
    lines.extend(all_deals)
    lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    deals = []
    deals.extend(scrape_hk_express())
    deals.extend(scrape_cathay())
    deals.extend(scrape_airasia())

    message = build_message(deals)
    success = send_telegram(message)

    if success:
        print("✅ Telegram 發送成功")
    else:
        print("❌ Telegram 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
