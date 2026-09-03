# SoSolsunday 改版設計規格 v2

> 給執行者（ChatGPT / Codex）的施工說明書。
> **參考實作已經寫好**：`docs/index.new.html` + `docs/assets/sosol.css`。
> 先把這兩個檔看完再動手；設計系統以 `sosol.css` 為唯一真相來源，不要在頁面裡另開色票。

---

## 0. 這次改版要解決什麼

現況問題：
1. **深藍 + 金色 + 白卡**的配色偏「金融儀表板」，跟旅遊情境不合，也跟同集團的 OkinawaSundays 完全對不上。
2. 首頁是 **tab 切換式 SPA**（首頁／旅遊優惠／目的地／季節限定），所有內容擠在同一個 URL，滑不到、也分享不出去。
3. 字級全部 10–13px，資訊密度很高但沒有層次，「哪個是重點」看不出來。
4. 三個子頁（destinations、seasonal、city）各自複製一份 CSS，改一次要改四個地方。

改版目標：
- 沿用 **OkinawaSundays 的視覺語言**（同一個品牌家族的感覺），但保留 SoSolsunday 自己的「價格速報」個性。
- 首頁改成**可以一路往下滑的 landing page**，不再用 tab 藏內容。
- 把新的**假期年曆**放上招牌位置 —— 這是這個站現在最有價值、別人沒有的東西。
- CSS 抽成一支共用檔，四個頁面共用。

**不要做的事**：不要改任何資料抓取邏輯（`flight_scraper.py`、`.github/workflows/`）、不要改 `docs/data/*.json` 的欄位結構、不要動 `docs/calendar/`（那頁已經是新設計系統，見第 6 節）。

---

## 1. 設計語言

### 色票（全部已定義在 `docs/assets/sosol.css` 的 `:root`）

| 變數 | 值 | 用在哪 |
|---|---|---|
| `--sand` | `#fff7e8` | **頁面底色**。這是最重要的一個 —— 舊版用米灰 `#F2EDE6`，新版是暖奶油色，整站的溫度差別就在這 |
| `--paper` | `#fffefb` | 卡片底色（不是純白） |
| `--navy` | `#062a3a` | 深色區塊、主按鈕、footer、大標題文字 |
| `--navy-2` | `#0b4052` | 漸層第二段 |
| `--blue` | `#087f9c` | 連結、eyebrow、hover 邊框 |
| `--lagoon` | `#79d9e6` | 裝飾色塊（hero blob、卡片右上角圓） |
| `--lagoon-soft` | `#dff7f8` | 淺色 hover 底 |
| `--sun` | `#ffd447` | **螢光筆底線**、次要 CTA 按鈕、深色底上的強調 |
| `--coral` | `#ff665a` | 週末日期、警示 |
| `--good / --warn / --bad` | `#0f9d76 / #d48b20 / #c03030` | 價格高低（沿用舊版語意，只是換了色值） |

**舊 → 新對照**（改子頁時直接套）：
```
--navy:#1B2F4A  →  --navy:#062a3a
--gold:#C9A84C  →  --sun:#ffd447   （但 gold 當「品牌強調色」時改用 --sun，當「連結色」時改用 --blue）
--sand:#F2EDE6  →  --sand:#fff7e8
--white:#fff    →  --paper:#fffefb
--text:#1E2D3D  →  --ink:#112f3b
--muted:#6B7D90 →  --muted:#5d737a
--green:#2D9B6F →  --good:#0f9d76
--amber:#D48B20 →  --warn:#d48b20
--red:#C03030   →  --bad:#c03030
```

### 字體
```css
font-family:"Noto Sans TC","PingFang TC","Hiragino Sans",system-ui,sans-serif;
```
不載外部字型檔（保持零相依、載入快）。

### 字級與層次（最關鍵的改動）
舊版全站 10–13px，新版拉開三個層級：

| 角色 | 大小 | 字重 | 字距 |
|---|---|---|---|
| Hero H1 | `clamp(2.6rem, 6.4vw, 5rem)` | 900 | `-.07em` |
| 區塊標題 H2 | `clamp(1.7rem, 3.4vw, 2.9rem)` | 900 | `-.05em` |
| Eyebrow（區塊上方小字） | `.72rem` 全大寫 | 900 | `.16em` |
| 內文 | `.9rem` | 400 | 0 |
| 附註 | `.74rem` | 700 | 0 |

**大標一律負字距 + 900 字重 + 行高 ≈1.0**，這是 OkinawaSundays 那個「厚實又緊」的感覺的來源。

### 形狀與陰影
- 圓角：大卡 `--radius-xl:32px`、一般卡 `--radius-lg:24px`、小元件 `--radius:16px`、pill `999px`
- 陰影只有兩階：`--shadow-sm`（靜態）、`--shadow`（hover）
- hover 一律 `transform:translateY(-2~3px)` + 陰影加深 + 邊框變 `--blue`

### 裝飾
- Hero 右上一顆會慢慢變形的 `--lagoon` 有機形色塊（`.hero::before`，12s 動畫）
- Hero 左下一個 coral 空心圓（`.hero::after`）
- 頁面底部固定的海浪 SVG（`.ocean-waves`，`position:fixed; z-index:-1`）—— 直接從 `okinews/templates/base.html` 複製那段 SVG
- `@media(prefers-reduced-motion:reduce)` 要關掉所有動畫（已寫在 sosol.css）

---

## 2. 首頁結構（`docs/index.html`）

**把現在的 tab 版整個換掉**，改成參考實作 `docs/index.new.html` 的單頁向下滑結構：

```
site-header（sticky、毛玻璃、捲動後加陰影）
  brand ☀ SoSolsunday ｜ nav: 首頁 · 機票·酒店 · 目的地 · 季節限定 · 假期年曆 ｜ 更新時間 pill
hero
  kicker pill「香港・台北出發 · 每日更新」
  H1「這個週末，/ 飛去哪？」← 第二行套 .play（藍字 + 黃色螢光筆底線）
  lead 一句話
  三顆 CTA：看今日最抵（primary）/ 📅 假期年曆（sun）/ 🌏 探索目的地（ghost）
  右側：「今日最低機票」卡片，列出 4 個目的地
statband  四格數字：最低來回機票 / 追蹤航線 / 季節限定活動 / 假期年曆國家
calband   ★ 假期年曆招牌區塊（見第 3 節）
#deals    本月最抵機票：香港/台北切換 → 橫捲價格卡 + 六個月價格表
          目的地：8 張大卡
          季節限定：本月 + 下月的活動卡（最多 6 張）
          週末酒店精選：週末日期切換 + 前 5 名
site-footer  深色三欄
```

**URL 規則**：`#deals` 用錨點捲動即可，不要再做 `display:none` 的 panel 切換。
`destinations/`、`seasonal/`、`calendar/` 維持獨立頁面。

---

## 3. 假期年曆招牌區塊（`.calband`）

這是這次改版的重點，**要放在首頁摺線下第一個大區塊**（statband 之後、機票之前）。

- 深色漸層卡（`--navy → --navy-2 → #0d5468`），右下一圈 lagoon 光暈
- 左側：eyebrow `FAMILY TRIP PLANNER` → H2「台港家人，什麼時候可以一起出發？」→ 一段說明 → 黃色 CTA「打開年曆 →」
- 右側 `.nextbox`：**即時算出「下一個台港共同連假」**
  - 讀 `docs/data/holidays.json`
  - 條件：台灣、香港雙方都放假、且至少有一天是國定假日、連續 ≥3 天、**兩邊都 0 請假**
  - 顯示：日期區間、連休天數、距今幾天、是哪兩個節日湊出來的
  - 例：`12/25(五) – 12/27(日) ／ 連休 3 天 · 還有 113 天 ／ 行憲紀念日 × 聖誕節翌日`
- 演算法已經寫在 `index.new.html` 的 `nextWindow()`，直接沿用

---

## 4. 元件清單（都在 `sosol.css`，直接用 class 不要重寫）

| class | 用途 |
|---|---|
| `.shell` / `.shell-narrow` | 版心（1180 / 780） |
| `.section` `.section-head` `.eyebrow` `.section-link` | 區塊標頭三件組 |
| `.pill` | 小標籤（含 `.dot` 綠點＝資料新鮮度） |
| `.btn` + `.btn-primary` / `.btn-sun` / `.btn-ghost` | 按鈕三態 |
| `.card` `.card-lg` `.card-head` `.card-title` | 白卡 |
| `.statband` `.stat` | 四格數字條 |
| `.hrow` + `.pcard` | 橫捲價格卡 |
| `.dgrid` + `.dcard` | 目的地大卡（右上角有 lagoon 圓，hover 會放大） |
| `.calband` `.nextbox` | 年曆招牌區塊 |
| `.elist` `.ecard` | 活動卡 |
| `.hlist` `.hrow-card` | 排行列（酒店、機票明細共用） |
| `.toggle` | 膠囊切換（香港/台北、週末日期） |
| `.site-header` `.site-footer` `.ocean-waves` | 站頭站尾與裝飾 |
| `.loading` `.nodata` | 空狀態 |

---

## 5. 子頁改法（destinations / city / seasonal）

三頁現在各自帶一份 `:root`，**全部刪掉**，改成：

```html
<link rel="stylesheet" href="../assets/sosol.css">
```

然後：
1. 舊的 `.hdr`（深藍橫條 + 金字）→ 換成首頁那個 `.site-header`（複製整段 HTML，把 `aria-current="page"` 移到對應項目，路徑加 `../`）
2. 舊的 `.sec-ttl`（11px 灰色大寫小標）→ 換成 `.section-head` 三件組（eyebrow + H2 + 說明）
3. 舊的 `.card` / `.chip` / `.ctab` / `.wtab` → 對應到 `.card` / `.dcard` / `.toggle`
4. 頁尾補上 `.site-footer`
5. 頁面底部補 `.ocean-waves` SVG

`city.html` 額外建議：在城市頁加一條「**這個城市今年的公眾假期**」小區塊，讀 `../data/holidays.json`，用城市 key 對到國家碼（沖繩/東京/福岡/石垣島/宮古島→JP，首爾/釜山→KR，台北→TW），列出未來 3 個假期並標「當地連假，人多」。這樣年曆的資料在目的地頁也發揮價值。

---

## 6. 假期年曆頁（`docs/calendar/`）—— 已完成，只差站頭站尾

`docs/calendar/index.html` 已經用同一組色票寫好了，**不要重寫**。它跟 `SunFamilyTrip/calendar.html` 是同一份檔案（md5 相同），改動會同時影響兩站。

只要做一件事：在 `docs/calendar/calendar-theme.css` 裡加樣式、或在頁面頂端插入 `.site-header` 的 HTML，讓它跟站上其他頁面一致。**HTML 本體如果非改不可，改完要 `cp` 一份到 `SunFamilyTrip/calendar.html`**。

資料檔 `docs/data/holidays.json` 是唯一真相來源，`SunFamilyTrip/holidays.json` 是副本。

---

## 7. RWD 斷點

| 斷點 | 行為 |
|---|---|
| `>900px` | hero 兩欄、目的地 4 欄、活動 3 欄、footer 3 欄 |
| `860px` | 桌機 nav 收成 ☰ 下拉 |
| `≤900px` | hero 單欄、目的地 2 欄、活動 1 欄 |
| `≤760px` | statband 2 欄 |
| `≤820px` | calband 單欄、footer 單欄 |

手機優先驗收：iPhone 375px 寬不能出現橫向捲動（`.hrow` 那種刻意橫捲的除外）。

---

## 8. 驗收清單

- [ ] 首頁不再有 tab 切換，一路往下滑就能看到全部內容
- [ ] 頁面底色是 `#fff7e8`（暖奶油），不是灰米色
- [ ] Hero H1 ≥ 42px，第二行有黃色螢光筆底線
- [ ] `.calband` 能算出正確的「下一個共同連假」（2026 應該是 12/25–12/27）
- [ ] 四個頁面都 link 同一支 `assets/sosol.css`，頁面內沒有殘留 `:root{--gold...}`
- [ ] 375px 寬無橫向捲動；Console 無 404、無 error
- [ ] 機票／酒店／季節限定資料照常渲染（JSON 結構未變）
- [ ] `docs/calendar/index.html` 與 `SunFamilyTrip/calendar.html` 內容仍然一致

---

## 9. 檔案清單

```
SoSolsunday/
├── DESIGN.md                     ← 本檔
└── docs/
    ├── assets/sosol.css          ← 設計系統（唯一色票來源）
    ├── index.new.html            ← 參考實作，驗收後改名蓋掉 index.html
    ├── index.html                ← 舊版，改完刪
    ├── calendar/                 ← 已是新設計，只補站頭站尾
    ├── data/holidays.json        ← 假期資料唯一真相來源
    ├── destinations/             ← 待改
    └── seasonal/                 ← 待改
```
