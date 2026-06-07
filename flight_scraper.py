import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# IATA → 中文城市名
CITIES = {
    "TYO": "東京", "NRT": "東京（成田）", "HND": "東京（羽田）",
    "OSA": "大阪", "KIX": "大阪（關西）", "OKA": "沖繩",
    "FUK": "福岡", "CTS": "札幌", "NGO": "名古屋",
    "SEL": "首爾", "ICN": "首爾（仁川）", "PUS": "釜山",
    "TPE": "台北", "KHH": "高雄", "RMQ": "台中",
    "BKK": "曼谷", "HKT": "普吉島", "CNX": "清邁",
    "SIN": "新加坡", "KUL": "吉隆坡", "PEN": "檳城",
    "DPS": "峇里", "CGK": "雅加達", "SUB": "泗水",
    "MNL": "馬尼拉", "CEB": "宿霧", "DVO": "棉蘭老",
    "HAN": "河內", "SGN": "胡志明市", "DAD": "峴港",
    "REP": "暹粒（吳哥窟）", "PNH": "金邊",
    "RGN": "仰光", "KTM": "加德滿都",
    "DEL": "新德里", "BOM": "孟買", "MAA": "清奈",
    "CMB": "可倫坡", "MLE": "馬爾代夫",
    "DXB": "杜拜", "DOH": "多哈", "AUH": "阿布扎比",
    "LHR": "倫敦", "CDG": "巴黎", "FRA": "法蘭克福",
    "AMS": "阿姆斯特丹", "ZRH": "蘇黎世", "VIE": "維也納",
    "FCO": "羅馬", "BCN": "巴塞隆拿", "MAD": "馬德里",
    "LIS": "里斯本", "ATH": "雅典",
    "SYD": "悉尼", "MEL": "墨爾本", "BNE": "布里斯本",
    "AKL": "奧克蘭",
    "LAX": "洛杉磯", "SFO": "三藩市", "JFK": "紐約",
    "YVR": "溫哥華", "YYZ": "多倫多",
}

# 航空公司代碼 → 中文名稱
AIRLINES = {
    "CX": "國泰航空", "UO": "香港快運", "HX": "香港航空",
    "GB": "大灣區航空", "SQ": "新加坡航空", "TG": "泰國航空",
    "MH": "馬來西亞航空", "JL": "日本航空", "NH": "全日空",
    "KE": "大韓航空", "OZ": "韓亞航空", "CI": "中華航空",
    "BR": "長榮航空", "EK": "阿聯酋航空", "QR": "卡塔爾航空",
    "EY": "阿提哈德", "TR": "酷航", "FD": "泰亞洲航空",
    "AK": "亞洲航空", "VN": "越南航空", "VJ": "越捷航空",
    "BA": "英國航空", "LH": "漢莎航空", "AF": "法國航空",
    "QF": "澳洲航空", "CA": "中國國際航空", "MU": "中國東方航空",
    "CZ": "中國南方航空",
}


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


def get_city(code: str) -> str:
    return CITIES.get(code, code)


def get_airline(code: str) -> str:
    return AIRLINES.get(code, code)


def fetch_cheapest_flights() -> list[dict]:
    """Travelpayouts：HKG 出發最平機票（按目的地）"""
    url = "https://api.travelpayouts.com/v1/prices/cheap"
    params = {
        "origin": "HKG",
        "currency": "hkd",
        "token": TRAVELPAYOUTS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=15)
    print(f"  cheap API 狀態: {resp.status_code}")
    print(f"  cheap API 回應: {resp.text[:400]}")
    resp.raise_for_status()
    data = resp.json()

    results = []
    if data.get("success") and data.get("data"):
        for dest_code, trips in data["data"].items():
            for _, trip in trips.items():
                results.append({
                    "dest": dest_code,
                    "city": get_city(dest_code),
                    "price": trip.get("price", 0),
                    "airline": get_airline(trip.get("airline", "")),
                    "depart": trip.get("departure_at", "")[:10],
                    "return": trip.get("return_at", "")[:10],
                    "direct": trip.get("number_of_changes", 1) == 0,
                })
    return sorted(results, key=lambda x: x["price"])


def fetch_latest_deals() -> list[dict]:
    """Travelpayouts：最新發現的低價機票"""
    url = "https://api.travelpayouts.com/v2/prices/latest"
    params = {
        "origin": "HKG",
        "currency": "hkd",
        "period_type": "year",
        "limit": 20,
        "show_to_affiliates": True,
        "token": TRAVELPAYOUTS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    if data.get("success") and data.get("data"):
        for item in data["data"]:
            results.append({
                "dest": item.get("destination", ""),
                "city": get_city(item.get("destination", "")),
                "price": item.get("price", 0),
                "airline": get_airline(item.get("airline", "")),
                "depart": item.get("departure_at", "")[:10],
                "return": item.get("return_at", "")[:10],
                "direct": item.get("number_of_changes", 1) == 0,
            })
    return sorted(results, key=lambda x: x["price"])


def scrape_hk_flight_news() -> list[str]:
    """Google News — 香港機票優惠新聞（7 天內）"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    seen = set()
    results = []
    queries = ["香港機票 特價 優惠", "HK Express 閃購", "國泰 機票優惠"]

    for query in queries:
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
            print(f"News 抓取失敗: {e}")

    return results[:8]


def format_flight(f: dict) -> str:
    direct = "直航 " if f["direct"] else ""
    ret = f" → 回程 {f['return']}" if f["return"] else ""
    return f"✈️ <b>{f['city']}</b>  HKD ${f['price']:,}  {direct}| {f['airline']} | 出發 {f['depart']}{ret}"


def build_message(cheapest: list, latest: list, news: list) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " HKT"
    lines = [
        "✈️ <b>香港出發每日機票特價報告</b>",
        f"🕐 {now_str}",
        "",
    ]

    if cheapest:
        lines.append("━━ 💰 <b>各目的地最低價</b> ━━")
        for f in cheapest[:10]:
            lines.append(format_flight(f))
        lines.append("")

    if latest:
        lines.append("━━ ⚡️ <b>最新低價發現</b> ━━")
        for f in latest[:8]:
            lines.append(format_flight(f))
        lines.append("")

    if news:
        lines.append("━━ 📰 <b>本週優惠新聞</b> ━━")
        lines.extend(news)
        lines.append("")

    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def main():
    token = TRAVELPAYOUTS_TOKEN or ""
    print(f"🔑 Token 長度: {len(token.strip())} 字符，前3位: {token.strip()[:3]}***")
    print("💰 查詢 HKG 各目的地最低價...")
    try:
        cheapest = fetch_cheapest_flights()
        print(f"  找到 {len(cheapest)} 個目的地")
    except Exception as e:
        print(f"  失敗: {e}")
        # Debug: 直接印出 API 回應
        try:
            r = requests.get(
                "https://api.travelpayouts.com/v1/prices/cheap",
                params={"origin": "HKG", "currency": "hkd", "token": TRAVELPAYOUTS_TOKEN},
                timeout=15
            )
            print(f"  API 狀態碼: {r.status_code}")
            print(f"  API 回應: {r.text[:300]}")
        except Exception as e2:
            print(f"  Debug 失敗: {e2}")
        cheapest = []

    print("⚡️ 查詢最新低價...")
    try:
        latest = fetch_latest_deals()
        print(f"  找到 {len(latest)} 條")
    except Exception as e:
        print(f"  失敗: {e}")
        try:
            r = requests.get(
                "https://api.travelpayouts.com/v2/prices/latest",
                params={"origin": "HKG", "currency": "hkd", "period_type": "year", "limit": 5, "token": TRAVELPAYOUTS_TOKEN},
                timeout=15
            )
            print(f"  API 狀態碼: {r.status_code}")
            print(f"  API 回應: {r.text[:300]}")
        except Exception as e2:
            print(f"  Debug 失敗: {e2}")
        latest = []

    print("📰 抓取優惠新聞...")
    news = scrape_hk_flight_news()
    print(f"  找到 {len(news)} 條新聞")

    message = build_message(cheapest, latest, news)
    success = send_telegram(message)

    if success:
        print(f"✅ 發送成功")
    else:
        print("❌ 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
