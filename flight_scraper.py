import os
import requests
from datetime import datetime, timedelta, timezone

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
TP_TOKEN           = os.environ["TRAVELPAYOUTS_TOKEN"]
LITEAPI_KEY        = os.environ["LITEAPI_KEY"]

HKT = timezone(timedelta(hours=8))

ROUTES = [
    ("HKG", "TPE", "🇭🇰→🇹🇼", "台北"),
    ("HKG", "OKA", "🇭🇰→🇯🇵", "沖繩"),
    ("TPE", "HKG", "🇹🇼→🇭🇰", "香港"),
    ("TPE", "OKA", "🇹🇼→🇯🇵", "沖繩"),
    ("OKA", "HKG", "🇯🇵→🇭🇰", "香港"),
    ("OKA", "TPE", "🇯🇵→🇹🇼", "台北"),
]

AIRLINE = {
    "UO": "香港快運", "CX": "國泰",    "HX": "香港航空",
    "IT": "台灣虎航", "MM": "樂桃",    "VZ": "VietJet",
    "JL": "日航",    "NH": "全日空",  "BR": "長榮",
    "CI": "中華航空", "TW": "T'way",  "3K": "捷星",
}


# ── Travelpayouts ──────────────────────────────────────────────────────────

def cheapest_6months(origin: str, dest: str) -> dict:
    today = datetime.now(HKT)
    results = {}
    for i in range(6):
        month = (today.replace(day=1) + timedelta(days=32 * i)).strftime("%Y-%m")
        url = (f"https://api.travelpayouts.com/v1/prices/cheap"
               f"?origin={origin}&destination={dest}&depart_date={month}"
               f"&currency=hkd&token={TP_TOKEN}")
        try:
            data = requests.get(url, timeout=10).json()
            if data.get("success") and data.get("data"):
                for _, transfers in data["data"].items():
                    for _, item in transfers.items():
                        p = item["price"]
                        if month not in results or p < results[month]["price"]:
                            results[month] = {
                                "price":   p,
                                "date":    item["departure_at"][:10],
                                "airline": AIRLINE.get(item["airline"], item["airline"]),
                            }
        except Exception as e:
            print(f"  TP {origin}→{dest} {month}: {e}")
    return results


# ── LiteAPI ────────────────────────────────────────────────────────────────

_hotels_cache = []

def get_hotels() -> list:
    global _hotels_cache
    r = requests.get(
        "https://api.liteapi.travel/v3.0/data/hotels"
        "?countryCode=JP&cityName=Naha&starRating=4&limit=10",
        headers={"X-API-Key": LITEAPI_KEY},
        timeout=15,
    )
    _hotels_cache = r.json().get("data", [])
    return _hotels_cache


def get_weekend_rates(hotel_ids: list, checkin: str, checkout: str) -> list:
    hotel_map = {h["id"]: h for h in _hotels_cache}
    try:
        data = requests.post(
            "https://api.liteapi.travel/v3.0/hotels/rates",
            headers={"X-API-Key": LITEAPI_KEY, "Content-Type": "application/json"},
            json={
                "hotelIds": hotel_ids,
                "checkin": checkin,
                "checkout": checkout,
                "currency": "HKD",
                "guestNationality": "HK",
                "occupancies": [{"adults": 2}],
            },
            timeout=20,
        ).json().get("data", [])
    except Exception as e:
        print(f"  LiteAPI {checkin}: {e}")
        return []

    results = []
    for h_info in data:
        hid = h_info.get("hotelId", "")
        h   = hotel_map.get(hid, {})
        min_price = None
        for room in h_info.get("roomTypes", []):
            for rate in room.get("rates", []):
                total = rate.get("retailRate", {}).get("total", [{}])
                p = total[0].get("amount") if total else None
                if p and (min_price is None or p < min_price):
                    min_price = p
        if min_price:
            results.append((min_price, h.get("name", hid), h.get("rating", "?")))
    return sorted(results)[:3]


def next_weekends(n: int = 3) -> list:
    today = datetime.now(HKT).date()
    days_to_fri = (4 - today.weekday()) % 7 or 7
    fri = today + timedelta(days=days_to_fri)
    return [(str(fri + timedelta(weeks=i)),
             str(fri + timedelta(weeks=i, days=2))) for i in range(n)]


# ── Message ────────────────────────────────────────────────────────────────

def build_message(flight_data: dict, hotel_weekends: list) -> str:
    now = datetime.now(HKT).strftime("%Y-%m-%d %H:%M")
    lines = [
        "✈️🏨 <b>機票 + 沖繩酒店 優惠速報</b>",
        f"🕐 {now} HKT",
        "",
        "━━ ✈️ <b>機票最低往返（未來6個月）</b> ━━",
    ]

    prev_origin = None
    for origin, dest, flag, dest_name in ROUTES:
        data = flight_data.get((origin, dest), {})
        if not data:
            continue
        origin_label = {"HKG": "🇭🇰 從香港", "TPE": "🇹🇼 從台北", "OKA": "🇯🇵 從沖繩"}[origin]
        if origin != prev_origin:
            lines.append(f"\n<b>{origin_label}</b>")
            prev_origin = origin
        best = min(data.values(), key=lambda x: x["price"])
        best_month = next(m for m, v in data.items() if v == best)
        lines.append(
            f"  {flag} {dest_name}  最低 <b>HK${best['price']:,}</b>"
            f" · {best_month} ({best['date'][5:]}) {best['airline']}"
        )

    if hotel_weekends:
        lines += ["", "━━ 🏨 <b>沖繩那覇 4星+ 酒店</b>（週末2晚·2人）━━"]
        for checkin, checkout, top3 in hotel_weekends:
            ci = datetime.strptime(checkin, "%Y-%m-%d")
            co = datetime.strptime(checkout, "%Y-%m-%d")
            lines.append(f"\n📅 {ci.strftime('%-m/%-d')}–{co.strftime('%-m/%-d')}")
            for price, name, rating in top3:
                short = (name[:24] + "…") if len(name) > 24 else name
                lines.append(f"  {short}  <b>HK${price:,.0f}</b> ⭐{rating}")

    lines += ["", "—— Sosol × Steve · Suniverse"]
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    if not r.ok:
        print(f"TG error {r.status_code}: {r.text}")
    return r.ok


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    # Flights
    print("✈️  拉機票...")
    flight_data = {}
    for origin, dest, _, _ in ROUTES:
        print(f"  {origin}→{dest}")
        flight_data[(origin, dest)] = cheapest_6months(origin, dest)

    # Hotels
    print("🏨  拉酒店...")
    hotels = get_hotels()
    hotel_ids = [h["id"] for h in hotels]
    hotel_weekends = []
    for checkin, checkout in next_weekends(3):
        print(f"  {checkin}~{checkout}")
        top3 = get_weekend_rates(hotel_ids, checkin, checkout)
        if top3:
            hotel_weekends.append((checkin, checkout, top3))

    msg = build_message(flight_data, hotel_weekends)
    print("\n── 預覽 ──\n" + msg + "\n──────────")

    if send_telegram(msg):
        print("✅ 發送成功")
    else:
        print("❌ 發送失敗")
        exit(1)


if __name__ == "__main__":
    main()
