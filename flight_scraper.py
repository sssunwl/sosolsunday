import os
import re
import json
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
}


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


def extract_embedded_json(soup: BeautifulSoup) -> list[dict]:
    """嘗試從頁面 <script> 標籤中提取嵌入的 JSON 資料"""
    results = []
    for script in soup.find_all("script", type="application/json"):
        try:
            data = json.loads(script.string)
            results.append(data)
        except Exception:
            pass
    return results


def scrape_hk_express() -> list[str]:
    """香港快運 HK Express — 促銷頁面"""
    deals = []
    urls_to_try = [
        "https://www.hkexpress.com/zh-hk/special-offer/",
        "https://www.hkexpress.com/en-hk/special-offer/",
        "https://www.hkexpress.com/zh-hk/promotions/",
    ]
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if not resp.ok:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            items = (
                soup.select("[class*='promo']")
                or soup.select("[class*='offer']")
                or soup.select("[class*='sale']")
                or soup.select("[class*='deal']")
                or soup.select("article")
            )
            for item in items[:5]:
                title = item.get_text(" ", strip=True)[:100]
                if len(title) > 8:
                    deals.append(f"<b>香港快運</b>：{translate_title(title)}")
            if deals:
                break
        except Exception:
            continue
    if not deals:
        deals.append("香港快運：優惠頁面無法讀取（JavaScript 渲染）")
    return deals


def scrape_hk_airlines() -> list[str]:
    """香港航空 — 促銷頁面"""
    deals = []
    try:
        url = "https://www.hongkongairlines.com/zh_HK/promotions"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = (
            soup.select("[class*='promo']")
            or soup.select("[class*='offer']")
            or soup.select("[class*='deal']")
            or soup.select("article")
            or soup.select(".card")
        )
        for item in items[:5]:
            title = item.get_text(" ", strip=True)[:100]
            if len(title) > 8:
                deals.append(f"<b>香港航空</b>：{translate_title(title)}")
    except Exception as e:
        deals.append(f"香港航空：無法讀取（{str(e)[:50]}）")
    if not deals:
        deals.append("香港航空：優惠頁面無法讀取（JavaScript 渲染）")
    return deals


def scrape_greater_bay() -> list[str]:
    """大灣區航空 — 促銷頁面"""
    deals = []
    urls_to_try = [
        "https://www.greater-bay-airlines.com/zh-hk/promotion",
        "https://www.greater-bay-airlines.com/en/promotion",
    ]
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if not resp.ok:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            items = (
                soup.select("[class*='promo']")
                or soup.select("[class*='offer']")
                or soup.select("[class*='deal']")
                or soup.select("article")
                or soup.select(".card")
            )
            for item in items[:5]:
                title = item.get_text(" ", strip=True)[:100]
                if len(title) > 8:
                    deals.append(f"<b>大灣區航空</b>：{translate_title(title)}")
            if deals:
                break
        except Exception:
            continue
    if not deals:
        deals.append("大灣區航空：優惠頁面無法讀取（JavaScript 渲染）")
    return deals


def scrape_cathay() -> list[str]:
    """國泰航空 — 嘗試靜態優惠頁面"""
    deals = []
    try:
        url = "https://www.cathaypacific.com/cx/zh_HK/offers/flights.html"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = (
            soup.select("[class*='offer']")
            or soup.select("[class*='promo']")
            or soup.select("article")
        )
        for item in items[:5]:
            title = item.get_text(" ", strip=True)[:100]
            if len(title) > 8:
                deals.append(f"<b>國泰航空</b>：{translate_title(title)}")
    except Exception as e:
        deals.append(f"國泰航空：無法讀取（{str(e)[:50]}）")
    if not deals:
        deals.append("國泰航空：優惠頁面無法讀取（JavaScript 渲染）")
    return deals


def scrape_secret_flying_hk() -> list[str]:
    """Secret Flying — 香港出發錯價 / 優惠（備用來源）"""
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
            deals.append("Secret Flying：今日暫無香港出發新優惠")
    except Exception as e:
        deals.append(f"Secret Flying 抓取失敗: {str(e)[:60]}")
    return deals


def build_message(sections: dict) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>香港出發航班優惠速報</b>",
        f"🕐 更新時間：{now_str}",
        "",
    ]
    for label, deals in sections.items():
        lines.append(f"━━ {label} ━━")
        lines.extend(deals)
        lines.append("")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    sections = {
        "🟠 香港快運": scrape_hk_express(),
        "🟡 香港航空": scrape_hk_airlines(),
        "🟢 大灣區航空": scrape_greater_bay(),
        "🔵 國泰航空": scrape_cathay(),
        "⚡️ 最新優惠（Secret Flying）": scrape_secret_flying_hk(),
    }

    message = build_message(sections)
    success = send_telegram(message)

    if success:
        print("✅ Telegram 發送成功")
    else:
        print("❌ Telegram 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
