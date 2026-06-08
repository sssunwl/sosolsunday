import os
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# 目的地 + 優惠關鍵字組合，比單純搜「機票優惠」更精準命中真正的促銷新聞
QUERIES = [
    "香港 東京 機票優惠",
    "香港 大阪 機票特價",
    "香港 沖繩 機票優惠",
    "香港 台北 機票優惠",
    "香港 首爾 機票特價",
    "香港 曼谷 機票優惠",
    "香港 新加坡 機票特價",
    "香港 峇里島 機票優惠",
    "國泰航空 機票優惠",
    "香港快運 HK Express 優惠",
]


def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
        timeout=10,
    )
    if not resp.ok:
        print(f"Telegram 錯誤: {resp.status_code} - {resp.text}")
    return resp.ok


def scrape_hk_flight_news() -> list[str]:
    """Google News — 香港出發機票優惠新聞（7 天內）"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    seen = set()
    results = []

    for query in QUERIES:
        try:
            encoded = requests.utils.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant"
            resp = requests.get(url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source = item.find("source").text if item.find("source") is not None else ""
                if not title or title in seen:
                    continue
                if pub:
                    try:
                        if parsedate_to_datetime(pub) < cutoff:
                            continue
                    except Exception:
                        pass
                seen.add(title)
                results.append(f'• <a href="{link}">{title}</a>  <i>— {source}</i>')
        except Exception as e:
            print(f"News 抓取失敗（{query}）: {e}")

    return results[:15]


def build_message(news: list) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>香港出發機票優惠快報</b>",
        f"🕐 {now_str}",
        "",
    ]

    if news:
        lines.append("━━ 📰 <b>近 7 天優惠新聞</b> ━━")
        lines.extend(news)
    else:
        lines.append("這次沒有抓到新的優惠新聞，明天再試。")

    lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    print("📰 抓取香港出發機票優惠新聞...")
    news = scrape_hk_flight_news()
    print(f"  找到 {len(news)} 條")

    message = build_message(news)
    success = send_telegram(message)

    if success:
        print("✅ 發送成功")
    else:
        print("❌ 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
