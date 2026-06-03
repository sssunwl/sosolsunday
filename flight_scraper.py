import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
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

# 城市 / 國家名稱對照表
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
    "Cebu": "宿霧", "Maldives": "馬爾代夫",
    "Non-stop": "直航", "roundtrip": "來回", "one-way": "單程",
    "for only": "只需", "USD": "美元", "EUR": "歐元",
}


def translate_title(title: str) -> str:
    """把英文標題翻譯成繁中（優先用對照表，再用 Google 翻譯）"""
    result = title
    for en, zh in TRANSLATIONS.items():
        result = re.sub(re.escape(en), zh, result, flags=re.IGNORECASE)
    # 如果大部分還是英文，呼叫 Google 翻譯
    en_ratio = sum(c.isascii() and c.isalpha() for c in result) / max(len(result), 1)
    if en_ratio > 0.4:
        try:
            result = GoogleTranslator(source="en", target="zh-TW").translate(result)
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


def scrape_secret_flying_hk() -> list[str]:
    """Secret Flying — 香港出發優惠機票"""
    deals = []
    try:
        url = "https://www.secretflying.com/posts/category/hong-kong/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for article in soup.select("article")[:8]:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""
            if title:
                zh_title = translate_title(title)
                deals.append(f'✈️ <a href="{link}">{zh_title}</a>')

        if not deals:
            deals.append("✈️ 香港出發：今日暫無新優惠")
    except Exception as e:
        deals.append(f"✈️ 香港出發抓取失敗: {str(e)[:80]}")

    return deals


def scrape_secret_flying_asia() -> list[str]:
    """Secret Flying — 亞洲其他出發優惠"""
    deals = []
    try:
        url = "https://www.secretflying.com/posts/category/asia/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for article in soup.select("article")[:6]:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""
            # 過濾掉香港出發（已在上面顯示）
            if title and "hong kong" not in title.lower():
                zh_title = translate_title(title)
                deals.append(f'🌏 <a href="{link}">{zh_title}</a>')

        if not deals:
            deals.append("🌏 亞洲其他優惠：今日暫無新資料")
    except Exception as e:
        deals.append(f"🌏 亞洲優惠抓取失敗: {str(e)[:80]}")

    return deals


def build_message(hk_deals: list[str], asia_deals: list[str]) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>每日航班優惠速報</b>",
        f"🕐 更新時間：{now_str}",
        "",
        "━━ 🇭🇰 <b>香港出發</b> ━━",
    ]
    lines.extend(hk_deals)
    lines.append("")
    lines.append("━━ 🌏 <b>亞洲其他出發</b> ━━")
    lines.extend(asia_deals)
    lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    hk_deals = scrape_secret_flying_hk()
    asia_deals = scrape_secret_flying_asia()

    message = build_message(hk_deals, asia_deals)
    success = send_telegram(message)

    if success:
        print("✅ Telegram 發送成功")
    else:
        print("❌ Telegram 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
