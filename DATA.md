# SoSolsunday 資料管線規格 v1 —— 「判斷引擎」改造

> 給執行者（Codex）的施工說明書。**只管資料管線，不碰前端。**
>
> - 前端改版規格 = `DESIGN.md`（管 `docs/**.html`、`docs/assets/`）
> - 本文件 = 資料管線（管 `flight_scraper.py`、`.github/workflows/`、`docs/data/*.json` 的**內容**）
> - 兩者唯一交界 = `docs/data/*.json` 的 schema。**本文件所有 schema 變更一律「只加不改」**，見第 9 節。

---

## 0. 這次要解決什麼

現況（2026-09-03 健檢結論）：管線本身健康，每日正常跑，**但產出的資料形態沒有決策價值**。

| # | 問題 | 證據 |
|---|---|---|
| 1 | 有價格、無「抵唔抵」 | `flights.json` 只有絕對價，無任何基準線。$1,302 是平是貴，讀者無從判斷 |
| 2 | **價格其實是單程，但全站當成「去某地的價錢」展示** | 已查證：`v1/prices/cheap` 不傳 `return_date` 即回傳單程。`flight_scraper.py:105` 正是不傳。讀者看到 $1,302 以為是來回，實際只是去程 |
| 3 | 機票與酒店 join 不起來 | 航班軸 =「每月最平」，酒店軸 =「未來三個週末」，兩條時間軸對不上 |
| 4 | 樣本過窄，且 `limit` 設定遠低於 API 上限 | `flight_scraper.py:160` 寫死 `starRating=4&limit=8`。已查證 LiteAPI `limit` 預設 200、上限 5000 —— 現在只取 8 間，等於自願放棄 96% 樣本 |
| 5 | 無行動出口 | 全 repo 無任何 affiliate marker 或訂購連結。讀者看完無法下一步 |

**改造目標**：把「報價表」變成「判斷引擎」。回答的問題從「幾錢？」變成 **「我下個假期，去邊度、幾時去、而家訂抵唔抵？」**

**非目標**：不做 Flyday / MeetHK / U Travel 那種促銷快報聚合。那是編輯部業務（人手盯快閃、與航空公司及旅行社有關係），爬蟲鬥不贏也守不住。促銷情報層留待日後另議。

---

## 1. 定位：三個新概念

```
       ┌─ 基準線 baseline ──── 這個價，相對過去 90 日是平是貴？
判斷引擎├─ 窗口 window ─────── 我實際放到假的是哪幾天？（HK + TW）
       └─ 套餐 package ────── 那幾天去某地，機＋酒總共要多少？
```

三者的關係：**窗口決定日期 → 日期同時餵給機票與酒店 → 得出套餐總成本 → 用基準線判斷抵不抵**。

其中 **baseline 是唯一無法被抄襲的資產**，因為它要靠時間累積。**因此第一階段最優先，越早開跑越好——每延一日就少一日歷史。**

---

## 2. 檔案佈局

```
data/history/                    ← 新增。原始歷史，NOT published（不在 docs/ 底下）
  flights.ndjson                 ← 每日 append，一行一筆
  hotels.ndjson
docs/data/                       ← published，前端讀這裡
  flights.json                   ← 既有，加欄位（只加不改）
  hotels.json                    ← 既有，加欄位（只加不改）
  packages.json                  ← 新增，本次核心產出
  holidays.json                  ← 既有，唯讀輸入，不要改
  seasonal.json                  ← 既有，本次不動
```

**為何 history 放 repo 根而不是 `docs/`**：前端只需要「算好的基準線」，不需要原始歷史。放 `docs/` 會被 GitHub Pages 公開發佈且拖慢頁面。體積估算：6 航線 × 6 月 × 365 日 ≈ 13k 行/年 ≈ 50KB/年（gzip 後更小），git 完全負擔得起。

`.gitignore` 現時不會排除 `data/`，**不要**把它加進去——歷史必須進版控，否則每次 CI 都從零開始。

---

## 3. Schema 規格

### 3.1 `data/history/flights.ndjson`（新增，內部）

一行一個 JSON object，每日 append：

```json
{"d":"2026-09-03","o":"HKG","dst":"TPE","m":"2026-11","p":1302,"dep":"2026-11-12","ret":"2026-11-16","al":"HB","rt":true}
```

| 欄位 | 意義 |
|---|---|
| `d` | 抓取日期（HKT） |
| `o` / `dst` | 出發／目的地 IATA |
| `m` | 出發月份 |
| `p` | 價格（HKD） |
| `dep` / `ret` | 去程／回程日期，`ret` 為 `null` 代表單程 |
| `al` | 航空公司代碼（存原始碼，不存中文名——中文名是展示層的事） |
| `rt` | `true` = 來回價，`false` = 單程價。**解決問題 #2 的關鍵欄位** |

欄位名刻意縮短：這個檔會長期累積，每個字元 × 13k 行/年。

### 3.2 `docs/data/flights.json`（既有，**只加不改**）

現有 `routes[].months[]` 的 `month` / `price` / `date` / `airline` / `is_cheapest` **一個都不准動**（前端改版正在進行中，改了會炸）。每個 month 物件**新增**：

```json
{
  "month": "2026-11", "price": 1302, "date": "2026-11-12",
  "airline": "北部灣航空", "is_cheapest": true,

  "return_date": "2026-11-16",
  "is_round_trip": true,
  "baseline": {
    "n_days": 90,
    "samples": 87,
    "median": 1655,
    "p10": 1288,
    "min": 1180,
    "max": 2340,
    "percentile": 8,
    "vs_median_pct": -21,
    "verdict": "great"
  }
}
```

**`is_round_trip` 的填法（已查證，不要猜）**：`v1/prices/cheap` 有無傳 `return_date` 決定回傳單程或來回。
- **價格軸**（`flights.json` 的 6 個月趨勢）：維持不傳 `return_date`，即**單程價**，`is_round_trip: false`。理由是單程價波動訊號較純，適合做基準線。
- **套餐**（`packages.json`）：傳 `return_date` 取**來回價**，`is_round_trip: true`。
- 兩者並存，靠此欄位區分。**前端必須顯示「單程／來回」標籤**，這是問題 #2 的正解。

`verdict` 列舉值（前端據此上色，語意沿用 `sosol.css` 的 `--good/--warn/--bad`）：

| 值 | 條件 | 建議文案 |
|---|---|---|
| `great` | `percentile <= 10` | 近 90 日最平 10% 🔥 |
| `good` | `percentile <= 30` | 低於平均 |
| `normal` | `percentile <= 70` | 一般水位 |
| `high` | `percentile > 70` | 偏貴，建議再等 |
| `unknown` | `samples < 14` | 資料累積中（第 N 日） |

**`unknown` 必須實作**：上線頭兩星期一定是這個狀態，前端要能優雅顯示「累積中」而不是顯示一個假的判斷。

### 3.3 `docs/data/packages.json`（新增，本次核心）

```json
{
  "updated_at": "2026-09-03 19:24 HKT",
  "windows": [
    {
      "key": "hk_2026_national_day",
      "market": "HK",
      "label": "國慶 + 中秋",
      "from": "2026-10-01",
      "to": "2026-10-05",
      "nights": 4,
      "source": "peaks",
      "days_until": 28,
      "packages": [
        {
          "dest": "OKA",
          "dest_name": "沖繩",
          "flight": {
            "price": 1580, "is_round_trip": true,
            "airline": "香港快運", "verdict": "good"
          },
          "hotel": {
            "name": "Nest酒店 那覇西", "rating": 8.6,
            "per_night": 543, "total": 2172
          },
          "total_pp": 3752,
          "verdict": "good",
          "baseline": { "median": 4410, "vs_median_pct": -15, "percentile": 22 }
        }
      ]
    }
  ]
}
```

`total_pp` = 每人總成本 = 機票 + (酒店總價 ÷ 2)。**酒店價除以 2 因為 LiteAPI 查的是 `occupancies:[{adults:2}]` 的房價**，這是雙人房總價不是人均。現行 code 沒有處理這件事，`hotels.json` 直接把雙人房價當成單一數字展示——**這是一個既有的呈現錯誤，本次一併修正**（在 `hotels.json` 新增 `per_person` 欄位，不動原 `price`）。

### 3.4 `docs/data/hotels.json`（既有，**只加不改**）

原有 `cities[].weekend_hotels[][]` 的 `name`/`price`/`rating`/`stars` 不動。每間酒店**新增**：

```json
{ "per_person": 543, "occupancy": 2, "baseline": { "...": "同 3.2" } }
```

---

## 4. 演算法規格

### 4.1 基準線 `baseline`

```
輸入：某 (origin, dest, month) 在 data/history/flights.ndjson 中，
      抓取日期 d 落在 [今日-90, 今日] 的所有 p
步驟：
  1. samples = 該集合大小
  2. samples < 14 → verdict = "unknown"，其餘統計欄位照算但前端不顯示
  3. median / p10 / min / max = 標準統計量
  4. percentile = (集合中 < 今日價的樣本數) ÷ samples × 100，四捨五入
  5. vs_median_pct = (今日價 - median) ÷ median × 100，四捨五入
  6. verdict 依 3.2 的表
```

**只用 stdlib `statistics`**，不要引入 numpy/pandas。`requirements.txt` 維持只有 `requests`。

`p10` 的插值法指定為 `statistics.quantiles(prices, n=10, method="inclusive")[0]`，樣本數為 1 時直接取該值。
百分比一律四捨五入（half away from zero），不要用 Python 內建 `round()` 的銀行家捨入。

**同一天多次執行**（例如手動 dispatch）：以 `(d, o, dst, m)` 為唯一鍵**覆寫**當日該筆，不要 append 出重複列，否則會扭曲樣本數。

### 4.2 窗口推導 `windows`

輸入 `docs/data/holidays.json`，對 `HK` 與 `TW` 兩個 `role: "home"` 的市場各自推導：

```
來源 A（優先）：years[YYYY][market].peaks[]
  → 已經是人手策展好的出遊高峰，直接採用，source = "peaks"

來源 B（補充）：由 holidays[] 自動推導連假
  → 把假期日 ∪ 週末日 攤平成日期集合，取所有「連續 ≥ 3 日」的區間
  → 與來源 A 有重疊者捨棄（peaks 優先），source = "derived"

來源 C（保底）：未來 8 個純週末（五→日）
  → source = "weekend"，讓淡季也有內容

過濾：只保留 from 在 [今日+3, 今日+180] 區間內的窗口
排序：依 from 昇冪
上限：每個 market 最多 12 個窗口
```

注意 `holidays[]` 的元素是 **array 不是 object**：`["2026-04-06", "清明節翌日", "sub"]`，第三個元素可選（`sub`=補假 / `half`=半日 / `est`=預估）。`est` 的假期照用但窗口要標 `"estimated": true`。

### 4.3 套餐組合 `packages`

```
對每個 window × 每個該市場的目的地：
  機票 = TP 查 v1/prices/cheap，帶齊 depart_date=window.from & return_date=window.to
         → 已查證：兩個日期都傳，回傳即為來回價，is_round_trip = true
  酒店 = LiteAPI rates 查 (city=dest 對應城市, checkin=window.from, checkout=window.to)
         取評分 ≥ 8.0 中最平的一間
  total_pp = flight.price + (hotel.total ÷ 2)
  該 window 內的 packages 依 total_pp 昇冪排序
```

`packages` 的 baseline 同樣寫進 `data/history/`，鍵為 `(market, window.key, dest)`。

---

## 5. 航線與城市設定（HK + TW 雙市場）

現行 `ROUTES` 的 6 條寫死航線（含 OKA 出發）**廢除**，改為 origin × dest 矩陣：

```python
MARKETS = {
    "HK": {"origin": "HKG", "name": "香港", "flag": "🇭🇰"},
    "TW": {"origin": "TPE", "name": "台北", "flag": "🇹🇼"},
}

# tier 1 = 每日抓；tier 2 = 每週一抓（見第 6 節預算）
DESTS = {
    "HK": [("TPE","台北",1), ("OKA","沖繩",1), ("NRT","東京",1), ("ICN","首爾",1),
           ("BKK","曼谷",1), ("KIX","大阪",2), ("FUK","福岡",2), ("PUS","釜山",2),
           ("SIN","新加坡",2), ("DAD","峴港",2), ("MNL","馬尼拉",2), ("CTS","札幌",2)],
    "TW": [("HKG","香港",1), ("OKA","沖繩",1), ("NRT","東京",1), ("ICN","首爾",1),
           ("KIX","大阪",1), ("FUK","福岡",2), ("PUS","釜山",2), ("BKK","曼谷",2),
           ("SIN","新加坡",2), ("DAD","峴港",2), ("CTS","札幌",2), ("MNL","馬尼拉",2)],
}
```

`DEST_CN`、`AIRLINE`、`HOTEL_CN` 三個對照表**保留沿用**，缺的補上。`HOTEL_CITIES` 需擴充以覆蓋新目的地。

### 5.1 酒店取樣修正（解決問題 #4）

現行 `starRating=4&limit=8` 兩個參數都要改。已查證的正確用法：

```
starRating   逗號分隔，且只接受 .0 / .5 兩種小數，範圍 1–5
             現行寫 "4" 格式不合規，可能被靜默忽略 → 改寫 "3.0,3.5,4.0,4.5,5.0"
limit        預設 200，上限 5000 → 改為 100（夠用且不浪費頻寬）
minRating    新增，設 7.5，濾走評分過低的
minReviewsCount  新增，設 50，濾走沒有評價基礎的新開業/幽靈酒店
```

取樣擴大後，每城市改為**分價位帶各取最平一間**（經濟 / 中價 / 高級），而非現行無差別取最平 2 間 —— 否則樣本再大，呈現出來還是只有最便宜那兩間。

---

## 6. API 預算與分層排程

現行約 **75 次/日**（TP 39 + LiteAPI 36）。若無腦全查：2 市場 × 12 目的地 × 12 窗口 = 288 次 TP + 288 次 LiteAPI rates，**會爆額度**。

分層策略：

| 排程 | 內容 | 估算呼叫 |
|---|---|---|
| 每日 08:00 HKT | tier 1 目的地 × 未來 4 個窗口 + 既有 6 個月價格軸 | TP ≈ 80、LiteAPI ≈ 40 |
| 每週一 08:00 | tier 2 目的地 × 未來 8 個窗口（全量刷新） | TP ≈ 160、LiteAPI ≈ 160 |

實作為**同一支 workflow 加 `if` 判斷**（`date +%u` = 1 時跑全量），不要開第二個 workflow 檔。

**已查證的額度現況**：

| API | 額度 | 對本專案的意義 |
|---|---|---|
| LiteAPI | 正式金鑰 **250 req/s**；sandbox 5 req/s。超額回 429 | 我們每日幾百次，**完全不是問題**。但要確認手上的 key 是正式還是 sandbox |
| Travelpayouts 資料 endpoint | **官方無公開文件** | 唯一有文件的是「Flights Search API 每 IP 每小時 200 次」，那是另一支 API，不適用。**這是本規格唯一未解的未知數** |

**必須做的防護**：
- TP 呼叫之間 `time.sleep(0.3)`（因額度未知，保守處理）；LiteAPI 不需要
- 收到 429 → 指數退避重試，最多 3 次
- ⚠️ **GitHub Actions runner 是共享 IP**。若 TP 真的按 IP 限流，可能被其他人的用量拖累。第一週要盯緊 log 的失敗率
- 任何一個目的地失敗 → 記 log、跳過、**沿用上一版該筆資料**，不要讓整個 job 失敗
- 若當日成功率 < 50%，**不要寫入 JSON、不要 commit**，直接 exit 1 讓 workflow 紅燈告警。寧可資料舊，不要資料錯

**現行 workflow 有一個沉默失敗風險**：`git diff --cached --quiet` 判斷無變化就跳過 commit。若 API 全掛而 code 寫出與昨日相同的檔案，會顯示「數據無變化」且 job 綠燈——外表完全正常。上述「成功率 < 50% 就 exit 1」即為此而設。

---

## 7. 變現與行動出口（解決問題 #5）

Travelpayouts **本身就是聯盟網絡**，目前只當免費資料源用，marker 未掛，讀者也無訂購連結。

- 在 `flights.json` / `packages.json` 的每筆加 `"url"` 欄位，指向帶 marker 的 Aviasales / Hotellook deeplink
- marker ID **不是機密**（本來就出現在公開 URL），可直接寫在 `flight_scraper.py` 的常數區，**不要**放 GitHub secrets（放了反而讓本地測試困難）
- 需要 SS 提供 Travelpayouts marker ID 才能實作。**此節在拿到 ID 前不要動工**

---

## 8. 施工階段（分三個 PR，不要一次過）

**PR 1 — 基準線地基**（最優先，先合併先開始累積歷史）
- 新增 `data/history/flights.ndjson` 寫入邏輯
- `flights.json` 加 `baseline` / `return_date` / `is_round_trip`
- **workflow 第 42 行的 `git add` 必須同時加上 `data/history/`**
- 全部 `verdict` 初期會是 `unknown`，正常
- 驗收：跑兩次（間隔改日期模擬），history 有 2 日資料且不重複

> ⚠️ **這一條是 PR 1 的成敗關鍵，v1 規格漏了。**
> CI runner 每次都是全新 checkout。若 `data/history/` 不進 `git add`，檔案每日重置為空，
> 基準線永遠累積不到樣本 —— PR 1 的唯一目的直接失效。
> 由 Codex 在 PR 1 實作時發現並回報。

**PR 2 — 窗口與套餐**
- 窗口推導（第 4.2 節）
- `packages.json` 產出
- `hotels.json` 加 `per_person`
- 驗收：`packages.json` 對 HK 與 TW 各至少產出 6 個窗口，每窗口至少 5 個目的地

**PR 3 — 航線擴充與分層排程**
- `MARKETS` / `DESTS` 矩陣
- workflow 加每週全量分支
- 驗收：連跑 7 日不觸發 rate limit

---

## 9. 硬性約束

1. **不准碰 `docs/**.html`、`docs/assets/`、`docs/calendar/`** —— 那是 `DESIGN.md` 的地盤，前端改版進行中
2. **不准改 `docs/data/holidays.json`** —— 唯讀輸入。它的唯一真相源在 `SoSolsunday/docs/data/`，`SunFamilyTrip` 是副本
3. **`docs/data/*.json` 既有欄位只加不改**：不准改名、不准刪除、不准改型別。前端正在改版，任何破壞性變更會讓兩邊同時炸
4. **`requirements.txt` 維持只有 `requests`** —— 統計用 stdlib `statistics`
5. **金鑰不進 repo** —— 沿用現有 4 個 GitHub secrets，不新增硬編碼
6. `data/history/` 必須進版控。這有**兩個**條件，缺一不可：
   - 不要加進 `.gitignore`
   - workflow 的 `git add` **必須包含 `data/history/`**（v1 規格只寫了前者，導致 PR 1 一度會靜默失效）

---

## 10. 查證結果（2026-09-04 完成，動工可直接採用）

| # | 問題 | 結論 | 影響 |
|---|---|---|---|
| 1 | `prices/cheap` 的 `price` 是單程還是來回？ | **不傳 `return_date` 就是單程。現行 code 正是不傳，所以全站現在顯示的是單程價** | 問題 #2 確認成立。見 3.2 節填法 |
| 2 | 有沒有 `return_date` 參數？ | **有**，接受 `yyyy-mm-dd` 或 `yyyy-mm` | 4.3 節的套餐查詢可以直接指定窗口起訖 |
| 3 | TP 資料 endpoint 額度上限？ | **官方無文件**。有文件的 200 次/小時/IP 屬另一支 Flights Search API | **唯一未解項**。按第 6 節保守處理並盯 log |
| 4 | LiteAPI `limit` 上限、`starRating` 可否多值？ | `limit` 預設 200、上限 5000；`starRating` 可逗號分隔但**只接受 .0/.5 小數**。另有 `minRating`、`minReviewsCount` 可用 | 現行 `limit=8` 放棄了 96% 樣本；`starRating=4` 格式不合規。見 5.1 節 |
| 5 | LiteAPI 額度？ | 正式金鑰 250 req/s，sandbox 5 req/s，超額回 429 | 非瓶頸。但要確認手上 key 的類型 |
| 6 | TP 有無促銷 endpoint？ | **有**：`aviasales/v3/get_special_offers`，參數 origin / destination / airline / locale / token，回傳帶 title 的促銷票價 | **推翻了原本「促銷層很貴」的判斷**。見第 11 節 |

仍需 SS 提供、無法自行查證的：
- **Travelpayouts marker ID**（第 7 節變現，缺此不動工）
- **手上的 LiteAPI key 是 sandbox 還是 production**（影響第 6 節排程密度）

## 11. 這份規格沒有涵蓋的

- **促銷情報層**（Flyday 式快閃快報）：本次不做，但**原因已經改變**。
  原判斷是「要做 newsletter 解析或爬促銷頁，貴且易碎」。查證後發現 TP 有現成的 `aviasales/v3/get_special_offers`，同一個 token 就能用，成本接近零。
  **修正後的建議**：等 PR 1–3 完成、baseline 有 30 日以上歷史之後，用一支獨立小 PR 接 `get_special_offers`，把促銷票價**餵進同一套 baseline 判斷**——變成「這個促銷相對過去 90 日到底有多抵」。這才是 Flyday 做不到、而你做得到的版本：**別人報促銷，你報這個促銷值不值**。
  Gmail newsletter 解析那條路留作後備，只在 `get_special_offers` 覆蓋率不足時才考慮
- **前端如何呈現**：本文件只定義資料契約。怎麼畫是 `DESIGN.md` 的事
- **推播/Telegram 文案**：現有 Telegram builder 沿用，待資料層穩定後另議
