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
    if not resp.ok:
        print(f"Telegram API 錯誤: {resp.status_code} - {resp.text}")
    return resp.ok


def scrape_secret_flying_hk() -> list[str]:
    """Secret Flying — 香港出發錯價 / 優惠機票"""
    deals = []
    try:
        url = "https://www.secretflying.com/posts/category/hong-kong/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        articles = soup.select("article")[:8]
        for article in articles:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""
            if title:
                deals.append(f'🟠 <a href="{link}">{title}</a>')

        if not deals:
            deals.append("🟠 Secret Flying HK: 今日暫無新優惠")
    except Exception as e:
        deals.append(f"🟠 Secret Flying 抓取失敗: {str(e)[:80]}")

    return deals


def scrape_the_flight_deal_asia() -> list[str]:
    """The Flight Deal — 亞洲出發優惠"""
    deals = []
    try:
        url = "https://www.theflightdeal.com/category/asia/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        articles = soup.select("article")[:6]
        for article in articles:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""
            if title:
                deals.append(f'🟢 <a href="{link}">{title}</a>')

        if not deals:
            deals.append("🟢 The Flight Deal Asia: 今日暫無新優惠")
    except Exception as e:
        deals.append(f"🟢 The Flight Deal 抓取失敗: {str(e)[:80]}")

    return deals


def scrape_secret_flying_asia() -> list[str]:
    """Secret Flying — 亞洲出發優惠（補充）"""
    deals = []
    try:
        url = "https://www.secretflying.com/posts/category/asia/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        articles = soup.select("article")[:5]
        for article in articles:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""
            if title:
                deals.append(f'🔴 <a href="{link}">{title}</a>')

        if not deals:
            deals.append("🔴 Secret Flying Asia: 今日暫無新優惠")
    except Exception as e:
        deals.append(f"🔴 Secret Flying Asia 抓取失敗: {str(e)[:80]}")

    return deals


def build_message(all_deals: list[str]) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>香港出發航班優惠</b>",
        f"🕐 更新時間：{now_str}",
        "",
    ]
    lines.extend(all_deals)
    lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    deals = []
    deals.extend(scrape_secret_flying_hk())
    deals.append("")
    deals.extend(scrape_the_flight_deal_asia())
    deals.append("")
    deals.extend(scrape_secret_flying_asia())

    message = build_message(deals)
    success = send_telegram(message)

    if success:
        print("✅ Telegram 發送成功")
    else:
        print("❌ Telegram 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
