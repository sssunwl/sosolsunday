import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from deep_translator import GoogleTranslator

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

TRANSLATIONS = {
    "Hong Kong": "香港", "Lisbon": "里斯本", "Portugal": "葡萄牙",
    "Delhi": "新德里", "India": "印度", "Zurich": "蘇黎世",
    "Switzerland": "瑞士", "Rome": "羅馬", "Italy": "意大利",
    "Melbourne": "墨爾本", "Australia": "澳洲", "London": "倫敦",
    "United Kingdom": "英國", "Paris": "巴黎", "France": "法國",
    "Tokyo": "東京", "Japan": "日本", "Seoul": "首爾",
    "South Korea": "韓國", "Bangkok": "曼谷", "Thailand": "泰國",
    "Singapore": "新加坡", "Taipei": "台北", "Taiwan": "台灣",
    "Bali": "峇里", "Indonesia": "印尼", "Vietnam": "越南",
    "Hanoi": "河內", "Ho Chi Minh": "胡志明市", "Osaka": "大阪",
    "New York": "紐約", "USA": "美國", "Los Angeles": "洛杉磯",
    "Dubai": "杜拜", "UAE": "阿聯酋", "Amsterdam": "阿姆斯特丹",
    "Netherlands": "荷蘭", "Barcelona": "巴塞隆拿", "Spain": "西班牙",
    "Madrid": "馬德里", "Frankfurt": "法蘭克福", "Germany": "德國",
    "Kuala Lumpur": "吉隆坡", "Malaysia": "馬來西亞",
    "Philippines": "菲律賓", "Manila": "馬尼拉",
    "Cebu": "宿霧", "Maldives": "馬爾代夫", "Okinawa": "沖繩",
    "Non-stop": "直航", "roundtrip": "來回", "one-way": "單程",
    "for only": "只需", "USD": "美元", "EUR": "歐元", "HKD": "港幣",
}

# Google News 搜尋關鍵詞（繁中，香港）
GOOGLE_NEWS_QUERIES = [
    "香港機票 特價 優惠",
    "香港快運 優惠",
    "國泰航空 機票 優惠",
    "香港航空 特價",
    "大灣區航空 優惠",
]


def translate_title(title: str) -> str:
    result = title
    for en, zh in TRANSLATIONS.items():
        result = re.sub(re.escape(en), zh, result, flags=re.IGNORECASE)
    en_ratio = sum(c.isascii() and c.isalpha() for c in result) / max(len(result), 1)
    if en_ratio > 0.5:
        try:
            result = GoogleTranslator(source="auto", target="zh-TW").translate(result)
        except Exception:
            pass
    return result


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


def scrape_google_news(query: str, cutoff: datetime, seen_titles: set) -> list[dict]:
    """從 Google News RSS 抓取指定關鍵詞的 7 天內新聞"""
    results = []
    try:
        encoded = requests.utils.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            source_el = item.find("source")

            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            source = source_el.text if source_el is not None else ""
            pub_str = pub_el.text if pub_el is not None else ""

            if not title or title in seen_titles:
                continue

            # 過濾 7 天內
            if pub_str:
                try:
                    pub_date = parsedate_to_datetime(pub_str)
                    if pub_date < cutoff:
                        continue
                except Exception:
                    pass

            seen_titles.add(title)
            results.append({
                "title": title,
                "link": link,
                "source": source,
                "pub": pub_str[:16] if pub_str else "",
            })

    except Exception as e:
        print(f"Google News 抓取失敗 ({query}): {e}")

    return results


def scrape_secret_flying_hk(cutoff: datetime) -> list[str]:
    """Secret Flying — 香港出發國際錯價 / 優惠"""
    deals = []
    try:
        url = "https://www.secretflying.com/posts/category/hong-kong/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for article in soup.select("article")[:20]:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            time_el = article.select_one("time[datetime]")

            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""

            if time_el and time_el.get("datetime"):
                try:
                    pub_date = datetime.fromisoformat(
                        time_el["datetime"].replace("Z", "+00:00")
                    )
                    if pub_date < cutoff:
                        continue
                except Exception:
                    pass

            if title:
                deals.append(f'<a href="{link}">{translate_title(title)}</a>')

        if not deals:
            deals.append("過去 7 天暫無香港出發國際新優惠")
    except Exception as e:
        deals.append(f"抓取失敗：{str(e)[:60]}")
    return deals


def build_message(news_items: list[dict], secret_deals: list[str]) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>香港出發航班優惠 — 每週精選</b>",
        f"🕐 更新時間：{now_str}",
        f"📅 過去 7 天最新資訊",
        "",
    ]

    if news_items:
        lines.append("━━ 📰 <b>各航空公司優惠新聞</b> ━━")
        for item in news_items[:12]:
            source = f" — {item['source']}" if item['source'] else ""
            lines.append(f'• <a href="{item["link"]}">{item["title"]}</a>{source}')
        lines.append("")
    else:
        lines.append("━━ 📰 過去 7 天暫無優惠新聞 ━━")
        lines.append("")

    lines.append("━━ 🌍 <b>國際錯價 / 特價（Secret Flying）</b> ━━")
    lines.extend(secret_deals)
    lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    seen_titles: set = set()
    all_news = []

    print("📰 抓取 Google News HK 航班優惠新聞...")
    for query in GOOGLE_NEWS_QUERIES:
        items = scrape_google_news(query, cutoff, seen_titles)
        all_news.extend(items)
        print(f"  '{query}': {len(items)} 條")

    # 按時間排序（最新在前）
    all_news.sort(key=lambda x: x["pub"], reverse=True)

    print("✈️ 抓取 Secret Flying 國際優惠...")
    secret_deals = scrape_secret_flying_hk(cutoff)

    message = build_message(all_news, secret_deals)
    success = send_telegram(message)

    if success:
        print(f"✅ Telegram 發送成功（{len(all_news)} 條新聞）")
    else:
        print("❌ Telegram 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
