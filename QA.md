# v2 改版驗收

驗收日期：2026-09-03。已完成本機改版，未提交、推送或部署；沿用既有 GitHub Pages 結構。（後記：改版初期的參考實作 `docs/index.new.html` 已於 2026-09-04 刪除，內容都在 `docs/index.html`。）

## 結果

- 首頁改為連續捲動 landing page，`#deals` 是錨點，不再切換隱藏面板。年曆招牌位於數字條之後、機票之前。
- 四個主頁共用 `docs/assets/sosol.css` 和 `docs/assets/site.js`，沒有頁面內舊色票。站頭、頁尾、海浪、選單及當前頁導覽一致。
- 375px：四種頁面、八個城市和年曆的頁面寬度均未溢出；首頁 H1 為 42px／900，底色為 `rgb(255, 247, 232)`，底線為 `rgb(255, 212, 71)`。
- 1440px：首頁 Hero 兩欄、目的地四欄、活動三欄、頁尾三欄。760／820／860／861／900／901px 斷點亦已核對。
- 2026-09-03 的下一個台港共同連假：12/25–12/27，連休 3 天、113 天後，台灣與香港均 0 天請假。節日包含行憲紀念日、聖誕節及聖誕節翌日。日期按台港時區計算。
- 香港／台北、酒店城市／週末、沖繩分區、季節月份／類型篩選、活动展開與無結果狀態均已驗證。手機選單支援 Escape 和導覽後收合。
- 城市頁顯示本年度未來三個公眾假期；連假達三天時標示當地人潮提醒。
- 年曆只修改 `calendar-theme.css`，以既有返回連結呈現品牌站頭並統一頁尾外觀，沒有插入另一套導航或改動年曆 HTML／功能。兩站年曆 HTML 仍完全一致，年曆正常顯示十二個月份。
- 使用全新本機來源複驗五個頁面，所有請求均為 200，沒有 404、console error 或 warning；本機連結、CSS、JavaScript 路徑與腳本語法亦通過測試。舊測試來源另有未被專案引用的 `/sw.js` 背景請求；新來源未再出現，未因此新增或改動 Service Worker。

## 資料與範圍

機酒資料仍為 2026-07-07 12:00 HKT，並非驗收當天的即時價格。首頁及更新標籤已明示資料日期；六個月價格表從當前月份開始，未有報價的月份顯示「—」，沒有補造價格或更動資料來源。

> **2026-09-04 後記**：上面的舊報價說明只適用於 9/3 的驗收快照。當時本機落後 origin/main 9 筆，遠端資料其實一直有更新；合併後機酒資料為 **2026-09-03 19:24 HKT**，每日管線正常，本文的「資料停在 7/7」不代表管線停更。合併時另發現遠端的「口袋地點」功能（`e0289f8`）尚未移植到 v2，詳見 README。

四個 `docs/data/*.json`、`flight_scraper.py`、`.github/workflows/flight_deals.yml` 及 `docs/calendar/index.html` 均以施工前後 SHA-1 比對，確認內容未改動。兩份年曆 HTML 的 SHA-1 均為 `5dd1525e0a695e21e847632211b1d81f2d6b5cb4`。

## 重跑測試

在 SoSolsunday 專案內執行：

```sh
node --test tests/frontend.test.cjs
git diff --check
```

14 項測試全部通過，涵蓋共同連假、跨年、補班、半日假、時區、城市假期、網路與 JSON 失敗狀態、現有資料渲染、無效城市、頁面結構、在地連結和年曆副本。測試無額外套件相依，亦不鎖定每日更新報價的檔案雜湊。

---

## 2026-09-04 併入 main 後重跑驗收

合併 `origin/main` 4 筆（PR #4 資料基準線 + 每日更新），機酒資料為 **2026-09-03 23:39 HKT**。

**測試**
- `node --test tests/frontend.test.cjs` — 14 項全過
- `python3 -m unittest discover -s tests -p test_baseline.py` — 10 項全過（新的資料管線測試）
- `git diff --check` 乾淨

**六個路徑逐一開過**：`/`、`/calendar/`、`/places/`、`/destinations/`、`/destinations/city.html?key=okinawa`、`/seasonal/`
全部 HTTP 200，console 無 error、無 warning，1180px 與 375px 都沒有橫向溢出，沒有殘留的載入中狀態。

**新資料帶出的一個問題（已修）**
`flights.json` 這次多了第三個出發地 **OKA（沖繩）**，共 2 條航線，但首頁的出發地切換是寫死的「香港／台北」兩顆按鈕，
等於有三分之一的航線在畫面上看不到。已改成**依 `routes` 的實際 origin 動態產生按鈕**，之後資料再加出發地不用改程式。

同時把 hero 的「今日最低機票」卡片鎖在有 `destinations` 彙整的出發地（HKG），不再跟著下方切換跑掉 —— 因為
`destinations` 只有 HKG／TPE 兩組，切到沖繩會讓 hero 整個空掉。沖繩出發的價格表正常顯示，
上方橫捲卡改為顯示「沖繩出發還沒有『本月最低』的彙整，往下看六個月價格表」。

**schema 相容性**：`months[]` 這次新增 `date`、`airline`、`is_cheapest`、`return_date`、`is_round_trip`、`baseline`，
原有的 `month`／`price` 未變動，前端照舊可讀。`baseline.verdict`（great／good／normal／high／unknown）目前前端還沒用上，
是之後可以拿來標「這個價格算不算便宜」的資料。
