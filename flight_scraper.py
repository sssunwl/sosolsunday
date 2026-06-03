import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from deep_translator import GoogleTranslator
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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
    "Sale": "特賣", "Promotion": "優惠", "Deal": "優惠",
    "Special offer": "特別優惠", "Flash sale": "閃購",
    "from": "出發", "to": "前往",
}

AIRLINES = [
    {
        "name": "香港快運",
        "url": "https://www.hkexpress.com/zh-hk/special-offer/",
        "selectors": ["[class*='promo']", "[class*='offer']", "[class*='sale']", "article", ".card"],
    },
    {
        "name": "香港航空",
        "url": "https://www.hongkongairlines.com/zh_HK/promotions",
        "selectors": ["[class*='promo']", "[class*='offer']", "[class*='deal']", "article", ".card"],
    },
    {
        "name": "大灣區航空",
        "url": "https://www.greater-bay-airlines.com/zh-hk/promotion",
        "selectors": ["[class*='promo']", "[class*='offer']", "[class*='deal']", "article", ".card"],
    },
    {
        "name": "國泰航空",
        "url": "https://www.cathaypacific.com/cx/zh_HK/offers/flights.html",
        "selectors": ["[class*='offer']", "[class*='promo']", "article", ".card"],
    },
]


def translate_title(title: str) -> str:
    result = title
    for en, zh in TRANSLATIONS.items():
        result = re.sub(re.escape(en), zh, result, flags=re.IGNORECASE)
    en_ratio = sum(c.isascii() and c.isalpha() for c in result) / max(len(result), 1)
    if en_ratio > 0.4:
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


def scrape_airline_playwright(page, airline: dict) -> list[str]:
    """用 Playwright 抓取航空公司優惠頁面"""
    deals = []
    name = airline["name"]
    try:
        page.goto(airline["url"], wait_until="domcontentloaded", timeout=25000)
        # 等待頁面 JS 渲染
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except PlaywrightTimeout:
            pass  # networkidle 超時沒關係，繼續解析

        content = page.content()
        soup = BeautifulSoup(content, "lxml")

        items = []
        for selector in airline["selectors"]:
            items = soup.select(selector)
            if items:
                break

        seen = set()
        for item in items[:6]:
            title = item.get_text(" ", strip=True)[:120]
            if len(title) > 8 and title not in seen:
                seen.add(title)
                deals.append(f"<b>{name}</b>：{translate_title(title)}")

        print(f"✅ {name}：找到 {len(deals)} 筆優惠")
    except Exception as e:
        print(f"❌ {name} 抓取失敗：{e}")
        deals.append(f"<b>{name}</b>：無法讀取優惠頁面")

    if not deals:
        deals.append(f"<b>{name}</b>：今日暫無優惠資料")

    return deals


def scrape_all_airlines() -> dict[str, list[str]]:
    """一次開瀏覽器，依序抓取所有航空公司"""
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="zh-HK",
        )
        page = context.new_page()
        for airline in AIRLINES:
            results[airline["name"]] = scrape_airline_playwright(page, airline)
        browser.close()
    return results


def scrape_secret_flying_hk() -> list[str]:
    """Secret Flying — 香港出發優惠（靜態備用來源）"""
    deals = []
    try:
        url = "https://www.secretflying.com/posts/category/hong-kong/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for article in soup.select("article")[:6]:
            title_el = article.select_one("h2, h3, .entry-title")
            link_el = article.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el["href"] if link_el else ""
            if title:
                deals.append(f'<a href="{link}">{translate_title(title)}</a>')
        if not deals:
            deals.append("今日暫無香港出發新優惠")
    except Exception as e:
        deals.append(f"抓取失敗：{str(e)[:60]}")
    return deals


def build_message(airline_results: dict, secret_flying: list[str]) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>香港出發航班優惠速報</b>",
        f"🕐 更新時間：{now_str}",
        "",
        "━━ 🏢 <b>航空公司官網優惠</b> ━━",
    ]
    for name, deals in airline_results.items():
        lines.extend(deals)
    lines.append("")
    lines.append("━━ ⚡️ <b>最新特價（Secret Flying）</b> ━━")
    lines.extend(secret_flying)
    lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    print("🚀 開始抓取航空公司官網（Playwright）...")
    airline_results = scrape_all_airlines()

    print("📰 抓取 Secret Flying...")
    secret_flying = scrape_secret_flying_hk()

    message = build_message(airline_results, secret_flying)
    success = send_telegram(message)

    if success:
        print("✅ Telegram 發送成功")
    else:
        print("❌ Telegram 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
