import json
import os
import requests
import statistics
from datetime import datetime, timedelta, timezone

HKT = timezone(timedelta(hours=8))
FLIGHT_HISTORY_PATH = "data/history/flights.ndjson"


def required_env(name: str) -> str:
    """Read a required secret only when a network operation needs it."""
    return os.environ[name]

# ── 航線設定 ───────────────────────────────────────────────────────────────

ROUTES = [
    ("HKG", "TPE", "🇭🇰→🇹🇼", "台北"),
    ("HKG", "OKA", "🇭🇰→🇯🇵", "沖繩"),
    ("TPE", "HKG", "🇹🇼→🇭🇰", "香港"),
    ("TPE", "OKA", "🇹🇼→🇯🇵", "沖繩"),
    ("OKA", "HKG", "🇯🇵→🇭🇰", "香港"),
    ("OKA", "TPE", "🇯🇵→🇹🇼", "台北"),
]

ORIGIN_NAMES = {"HKG": "香港", "TPE": "台北", "OKA": "沖繩"}

AIRLINE = {
    "UO": "香港快運", "CX": "國泰",    "HX": "香港航空",
    "IT": "台灣虎航", "MM": "樂桃",    "VZ": "VietJet",
    "JL": "日航",    "NH": "全日空",  "BR": "長榮",
    "CI": "中華航空", "TW": "T'way",  "3K": "捷星",
    "5J": "宿霧太平洋", "FM": "上海航空", "HB": "北部灣航空",
}

DEST_CN = {
    "TPE": "台北", "TSA": "台北", "KHH": "高雄", "RMQ": "台中",
    "OKA": "沖繩那覇", "ISG": "石垣島", "MMY": "宮古島",
    "ICN": "首爾", "GMP": "首爾", "PUS": "釜山", "CJU": "濟州",
    "NRT": "東京", "HND": "東京", "KIX": "大阪", "ITM": "大阪",
    "FUK": "福岡", "CTS": "札幌", "NGO": "名古屋",
    "MNL": "馬尼拉", "CEB": "宿霧",
    "BKK": "曼谷", "DMK": "曼谷", "HKT": "普吉", "CNX": "清邁",
    "SIN": "新加坡", "KUL": "吉隆坡", "DPS": "峇里島",
    "HAN": "河內", "SGN": "胡志明", "DAD": "峴港",
    "PEK": "北京", "BJS": "北京", "SHA": "上海", "PVG": "上海",
    "CAN": "廣州", "SZX": "深圳", "CTU": "成都",
    "SYX": "三亞", "KWL": "桂林", "NGB": "寧波",
    "HKG": "香港", "MFM": "澳門",
    "SEL": "首爾", "GMP": "首爾",
    "PQC": "富國島", "VTE": "永珍", "REP": "暹粒",
    "CMB": "可倫坡", "BOM": "孟買", "DEL": "新德里",
    "SYD": "悉尼", "MEL": "墨爾本",
    "LHR": "倫敦", "CDG": "巴黎", "FCO": "羅馬",
}

# ── 酒店設定 ───────────────────────────────────────────────────────────────

HOTEL_CITIES = [
    ("JP", "Naha",        "🇯🇵 沖繩南部・那霸", "okinawa_south"),
    ("JP", "Onna",        "🇯🇵 沖繩中部",      "okinawa_central"),
    ("JP", "Nago",        "🇯🇵 沖繩北部",      "okinawa_north"),
    ("JP", "Ishigaki",    "🇯🇵 石垣島",        "ishigaki"),
    ("JP", "Miyakojima",  "🇯🇵 宮古島",        "miyakojima"),
    ("JP", "Fukuoka",     "🇯🇵 福岡",          "fukuoka"),
    ("JP", "Tokyo",       "🇯🇵 東京",          "tokyo"),
    ("KR", "Seoul",       "🇰🇷 首爾",          "seoul"),
    ("KR", "Busan",       "🇰🇷 釜山",          "busan"),
]

HOTEL_CN = {
    "JR Kyushu Hotel Blossom Naha":                          "JR九州酒店 那覇",
    "Hotel Aqua Citta Naha":                                 "Aqua Citta酒店 那覇",
    "Loisir Hotel Naha":                                     "Loisir酒店 那覇",
    "Nest Hotel Naha Nishi":                                 "Nest酒店 那覇西",
    "Okinawa NaHaNa Hotel & Spa":                            "沖繩NaHaNa酒店&水療",
    "Novotel Okinawa Naha":                                  "諾富特沖繩那覇",
    "DoubleTree by Hilton Naha":                             "希爾頓逸林那覇",
    "Hotel Palm Royal Resort Kokusai Street":                "棕欄皇家渡假酒店 國際通",
    "HOTEL STRATA NAHA":                                     "STRATA酒店 那覇",
    "Daiwa Roynet Hotel Naha Kokusaidori":                   "大和Roynet那覇 國際通",
    "GLAD Mapo":                                             "GLAD麻浦酒店",
    "LOTTE CITY HOTEL Myeongdong":                           "樂天城市酒店 明洞",
    "Shilla Stay Busan Haeundae":                            "新羅住宿 釜山海雲台",
    "Best Western Haeundae Hotel":                           "最佳西方 海雲台酒店",
    "EXES ISHIGAKI":                                         "EXES石垣島酒店",
    "palmvilla ishigakijima karei":                          "Palm Villa石垣島",
    "Miyakojima Tokyu Hotel & Resorts":                      "宮古島東急飯店",
    "Allamanda Imgya Coral Village":                         "Allamanda伊武野珊瑚村",
    "Mitsui Garden Hotel Fukuoka Gion":                      "三井花園酒店 福岡祇園",
    "Hotel JAL City Fukuoka Tenjin":                         "JAL城市酒店 福岡天神",
    "Villa Fontaine Grand Haneda Airport - Directly connected to Haneda Airport Terminal 3": "Villa Fontaine 羽田機場",
    "Tokyo Bay Shiomi Prince Hotel":                         "東京灣汐見王子酒店",
}

def hotel_name_cn(name: str) -> str:
    return HOTEL_CN.get(name, name)


# ── Travelpayouts ──────────────────────────────────────────────────────────

def cheapest_6months(origin: str, dest: str) -> dict:
    today = datetime.now(HKT)
    tp_token = required_env("TRAVELPAYOUTS_TOKEN").strip()
    results = {}
    for i in range(6):
        month = (today.replace(day=1) + timedelta(days=32 * i)).strftime("%Y-%m")
        url = (f"https://api.travelpayouts.com/v1/prices/cheap"
               f"?origin={origin}&destination={dest}&depart_date={month}"
               f"&currency=hkd&token={tp_token}")
        try:
            r = requests.get(url, timeout=10)
            if not r.ok or not r.text.strip():
                continue
            data = r.json()
            if data.get("success") and data.get("data"):
                for _, transfers in data["data"].items():
                    for _, item in transfers.items():
                        p = item["price"]
                        if month not in results or p < results[month]["price"]:
                            return_at = item.get("return_at")
                            results[month] = {
                                "price":        p,
                                "date":         item["departure_at"][:10],
                                "return_at":    return_at[:10] if return_at else None,
                                "airline":      AIRLINE.get(item["airline"], item["airline"]),
                                "airline_code": item["airline"],
                                "is_round_trip": False,
                            }
        except Exception as e:
            print(f"  TP {origin}→{dest} {month}: {e}")
    return results


def cheapest_destinations(origin: str, top: int = 5) -> list:
    month = datetime.now(HKT).strftime("%Y-%m")
    tp_token = required_env("TRAVELPAYOUTS_TOKEN").strip()
    url = (f"https://api.travelpayouts.com/v1/prices/cheap"
           f"?origin={origin}&currency=hkd&token={tp_token}"
           f"&depart_date={month}&limit=15")
    items = []
    try:
        r = requests.get(url, timeout=10)
        if not r.ok or not r.text.strip():
            return []
        data = r.json()
        if data.get("success") and data.get("data"):
            for dest_code, transfers in data["data"].items():
                for _, item in transfers.items():
                    name = DEST_CN.get(dest_code, dest_code)
                    items.append((item["price"], name, dest_code))
    except Exception as e:
        print(f"  dest {origin}: {e}")
    return sorted(items)[:top]


# ── LiteAPI ────────────────────────────────────────────────────────────────

_hotel_cache = {}

def get_hotels(country: str, city: str) -> list:
    key = f"{country}/{city}"
    if key in _hotel_cache:
        return _hotel_cache[key]
    try:
        r = requests.get(
            f"https://api.liteapi.travel/v3.0/data/hotels"
            f"?countryCode={country}&cityName={city}&starRating=4&limit=8",
            headers={"X-API-Key": required_env("LITEAPI_KEY").strip()},
            timeout=15,
        )
        hotels = r.json().get("data", []) if r.ok else []
    except Exception as e:
        print(f"  hotels {city}: {e}")
        hotels = []
    _hotel_cache[key] = hotels
    return hotels


def get_rates(hotel_ids: list, hotel_map: dict, checkin: str, checkout: str, top: int = 2) -> list:
    if not hotel_ids:
        return []
    try:
        r = requests.post(
            "https://api.liteapi.travel/v3.0/hotels/rates",
            headers={"X-API-Key": required_env("LITEAPI_KEY").strip(), "Content-Type": "application/json"},
            json={
                "hotelIds": hotel_ids,
                "checkin": checkin,
                "checkout": checkout,
                "currency": "HKD",
                "guestNationality": "HK",
                "occupancies": [{"adults": 2}],
            },
            timeout=20,
        )
        data = r.json().get("data", []) if r.ok else []
    except Exception as e:
        print(f"  rates {checkin}: {e}")
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
            results.append((min_price, hotel_name_cn(h.get("name", hid)), h.get("rating", "?")))
    return sorted(results)[:top]


def next_3_weekends() -> list:
    today = datetime.now(HKT).date()
    days_to_fri = (4 - today.weekday()) % 7 or 7
    weekends = []
    for i in range(3):
        fri = today + timedelta(days=days_to_fri + 7 * i)
        sun = fri + timedelta(days=2)
        weekends.append({
            "label":   f"{fri.month}/{fri.day}–{sun.day}",
            "checkin":  str(fri),
            "checkout": str(sun),
        })
    return weekends


# ── Flight history and baseline ───────────────────────────────────────────

def _round_half_up(value: float) -> int:
    """Round halves away from zero, matching 四捨五入 semantics."""
    return int(value + 0.5) if value >= 0 else int(value - 0.5)


def calculate_baseline(historical_prices: list, current_price: int) -> dict:
    """Calculate a 90-day price baseline without performing any I/O."""
    prices = list(historical_prices)
    samples = len(prices)
    baseline = {
        "n_days": 90,
        "samples": samples,
        "median": None,
        "p10": None,
        "min": None,
        "max": None,
        "percentile": None,
        "vs_median_pct": None,
        "verdict": "unknown",
    }
    if not prices:
        return baseline

    median = statistics.median(prices)
    p10 = prices[0] if samples == 1 else statistics.quantiles(
        prices, n=10, method="inclusive"
    )[0]
    percentile = _round_half_up(
        sum(price < current_price for price in prices) / samples * 100
    )
    vs_median_pct = (
        _round_half_up((current_price - median) / median * 100)
        if median else None
    )

    if samples < 14:
        verdict = "unknown"
    elif percentile <= 10:
        verdict = "great"
    elif percentile <= 30:
        verdict = "good"
    elif percentile <= 70:
        verdict = "normal"
    else:
        verdict = "high"

    baseline.update({
        "median": median,
        "p10": p10,
        "min": min(prices),
        "max": max(prices),
        "percentile": percentile,
        "vs_median_pct": vs_median_pct,
        "verdict": verdict,
    })
    return baseline


def write_flight_history(flight_data: dict, scrape_date=None,
                         path: str = FLIGHT_HISTORY_PATH) -> None:
    """Upsert scraped fares by (date, origin, destination, month)."""
    scrape_date = scrape_date or datetime.now(HKT).date()
    scrape_date_str = scrape_date.isoformat()
    records = {}

    if os.path.exists(path):
        with open(path, encoding="utf-8") as history_file:
            for line_number, line in enumerate(history_file, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    key = (record["d"], record["o"], record["dst"], record["m"])
                except (json.JSONDecodeError, KeyError) as error:
                    raise ValueError(
                        f"Invalid flight history at {path}:{line_number}"
                    ) from error
                records[key] = record

    for (origin, dest), monthly_fares in flight_data.items():
        for month, fare in monthly_fares.items():
            record = {
                "d": scrape_date_str,
                "o": origin,
                "dst": dest,
                "m": month,
                "p": fare["price"],
                "dep": fare["date"],
                "ret": fare.get("return_at"),
                "al": fare["airline_code"],
                "rt": fare.get("is_round_trip", False),
            }
            records[(scrape_date_str, origin, dest, month)] = record

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary_path = f"{path}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as history_file:
        for record in records.values():
            history_file.write(json.dumps(
                record, ensure_ascii=False, separators=(",", ":")
            ) + "\n")
    os.replace(temporary_path, path)


def load_recent_flight_prices(as_of_date=None,
                              path: str = FLIGHT_HISTORY_PATH) -> dict:
    """Group prices whose HKT scrape date is in [as_of_date - 90, as_of_date]."""
    as_of_date = as_of_date or datetime.now(HKT).date()
    cutoff = as_of_date - timedelta(days=90)
    grouped = {}
    if not os.path.exists(path):
        return grouped

    with open(path, encoding="utf-8") as history_file:
        for line_number, line in enumerate(history_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                record_date = datetime.strptime(record["d"], "%Y-%m-%d").date()
                key = (record["o"], record["dst"], record["m"])
                price = record["p"]
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid flight history at {path}:{line_number}"
                ) from error
            if cutoff <= record_date <= as_of_date:
                grouped.setdefault(key, []).append(price)
    return grouped


# ── JSON export ────────────────────────────────────────────────────────────

def write_json_files(flight_data: dict, destinations: dict,
                     hotel_all: list, weekends: list,
                     flight_history: dict = None) -> None:
    os.makedirs("docs/data", exist_ok=True)
    now_str = datetime.now(HKT).strftime("%Y-%m-%d %H:%M HKT")
    flight_history = flight_history or {}

    # flights.json
    routes_json = []
    for origin, dest, flag, dest_name in ROUTES:
        data = flight_data.get((origin, dest), {})
        if not data:
            continue
        best_price = min(v["price"] for v in data.values())
        months = [
            {
                "month":       m,
                "price":       data[m]["price"],
                "date":        data[m]["date"],
                "airline":     data[m]["airline"],
                "is_cheapest": data[m]["price"] == best_price,
                "return_date": None,
                "is_round_trip": False,
                "baseline": calculate_baseline(
                    flight_history.get((origin, dest, m), []), data[m]["price"]
                ),
            }
            for m in sorted(data)
        ]
        routes_json.append({
            "key":         f"{origin}_{dest}",
            "origin":      origin,
            "dest":        dest,
            "origin_name": ORIGIN_NAMES[origin],
            "dest_name":   dest_name,
            "flag":        flag,
            "months":      months,
        })

    dest_json = {
        code: [{"price": p, "name": name, "code": c} for p, name, c in items]
        for code, items in destinations.items()
    }

    with open("docs/data/flights.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now_str, "routes": routes_json, "destinations": dest_json},
                  f, ensure_ascii=False, indent=2)
    print("✅ docs/data/flights.json 寫入完成")

    # hotels.json
    cities_json = []
    for city_label, city_key, per_weekend in hotel_all:
        parts = city_label.split(" ", 1)
        flag = parts[0] if len(parts) > 1 else ""
        name = parts[1] if len(parts) > 1 else city_label
        weekend_hotels = []
        for top2 in per_weekend:
            weekend_hotels.append([
                {
                    "name":   nm,
                    "price":  round(price),
                    "rating": float(rating) if rating != "?" else 0,
                    "stars":  4,
                }
                for price, nm, rating in top2
            ])
        cities_json.append({
            "key":            city_key,
            "name":           name,
            "flag":           flag,
            "weekend_hotels": weekend_hotels,
        })

    with open("docs/data/hotels.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now_str, "weekends": weekends, "cities": cities_json},
                  f, ensure_ascii=False, indent=2)
    print("✅ docs/data/hotels.json 寫入完成")


# ── Telegram message builders ──────────────────────────────────────────────

def build_flights_msg(flight_data: dict, destinations: dict) -> str:
    now = datetime.now(HKT).strftime("%Y-%m-%d %H:%M")
    lines = [
        "✈️ <b>機票優惠速報</b>",
        f"🕐 {now} HKT",
        "",
        "━━ <b>每月最低往返（未來6個月）</b> ━━",
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

        best_price = min(v["price"] for v in data.values())
        month_parts = []
        for m in sorted(data):
            v = data[m]
            tag = "★" if v["price"] == best_price else ""
            month_parts.append(f"{m[5:]}月 <b>${v['price']:,}</b>{tag}")
        lines.append(f"  {flag} {dest_name}  " + "  ".join(month_parts))

    lines += ["", "━━ <b>本月從各地出發最便宜</b> ━━"]
    for origin_code, label in [("HKG", "🇭🇰 香港"), ("TPE", "🇹🇼 台北")]:
        dests = destinations.get(origin_code, [])
        if not dests:
            continue
        dest_parts = [f"{name} <b>${p:,}</b>" for p, name, _ in dests]
        lines.append(f"\n<b>{label}</b>")
        lines.append("  " + "  ·  ".join(dest_parts))

    lines += ["", "🌐 sssunwl.github.io/sosolsunday", "—— Sosol × Steve · Suniverse"]
    return "\n".join(lines)


def build_hotels_msg(hotel_all: list, weekends: list) -> str:
    wknd = weekends[0]
    ci = datetime.strptime(wknd["checkin"], "%Y-%m-%d")
    co = datetime.strptime(wknd["checkout"], "%Y-%m-%d")
    lines = [
        "🏨 <b>亞洲酒店報價</b>",
        f"📅 {ci.strftime('%-m/%-d')}–{co.strftime('%-m/%-d')} 週末2晚·2人·4星+",
        "",
    ]
    for city_label, city_key, per_weekend in hotel_all:
        top2 = per_weekend[0] if per_weekend else []
        if not top2:
            continue
        lines.append(f"<b>{city_label}</b>")
        for price, name, rating in top2:
            lines.append(f"  {name}  <b>HK${price:,.0f}</b> ⭐{rating}")
        lines.append("")
    lines.append("🌐 sssunwl.github.io/sosolsunday")
    lines.append("—— Sosol × Steve · Suniverse")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{required_env('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={
            "chat_id": required_env("TELEGRAM_CHAT_ID"),
            "text": text,
            "parse_mode": "HTML",
        },
        timeout=10,
    )
    if not r.ok:
        print(f"TG error {r.status_code}: {r.text[:200]}")
    return r.ok


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    scrape_date = datetime.now(HKT).date()

    # Flights
    print("✈️  拉機票...")
    flight_data = {}
    for origin, dest, _, _ in ROUTES:
        print(f"  {origin}→{dest}")
        flight_data[(origin, dest)] = cheapest_6months(origin, dest)

    # Upsert history before calculating the published baseline, so today's
    # observation is included once in the current 90-day window.
    write_flight_history(flight_data, scrape_date)
    flight_history = load_recent_flight_prices(scrape_date)

    print("🔍  拉最便宜目的地...")
    destinations = {}
    for origin in ["HKG", "TPE"]:
        print(f"  from {origin}")
        destinations[origin] = cheapest_destinations(origin, top=5)

    # Hotels — 3 weekends × 7 cities
    weekends = next_3_weekends()
    print(f"🏨  拉酒店（{weekends[0]['checkin']} / {weekends[1]['checkin']} / {weekends[2]['checkin']}）...")

    hotel_all = []
    for country, city, city_label, city_key in HOTEL_CITIES:
        hotels = get_hotels(country, city)
        if not hotels:
            print(f"  {city}: 無酒店")
            continue
        hotel_map = {h["id"]: h for h in hotels}
        hotel_ids = [h["id"] for h in hotels]
        per_weekend = []
        for wknd in weekends:
            top2 = get_rates(hotel_ids, hotel_map, wknd["checkin"], wknd["checkout"], top=2)
            per_weekend.append(top2)
        print(f"  {city}: {sum(len(w) for w in per_weekend)} 間報價（3週）")
        hotel_all.append((city_label, city_key, per_weekend))

    # Write JSON for website
    write_json_files(
        flight_data, destinations, hotel_all, weekends, flight_history
    )

    # Send Telegram
    msg1 = build_flights_msg(flight_data, destinations)
    msg2 = build_hotels_msg(hotel_all, weekends)

    print("\n── 機票預覽 ──\n" + msg1)
    print("\n── 酒店預覽 ──\n" + msg2)

    ok1 = send_telegram(msg1)
    ok2 = send_telegram(msg2)

    if ok1 and ok2:
        print("✅ 兩則訊息發送成功")
    else:
        print(f"❌ msg1={'OK' if ok1 else 'FAIL'}  msg2={'OK' if ok2 else 'FAIL'}")
        exit(1)


if __name__ == "__main__":
    main()
