# SoSolsunday

靜態旅遊網站，公開頁面放在 `docs/`，沿用既有 GitHub Pages 部署方式。

- 改版依 `DESIGN.md` 與 `docs/index.new.html`；設計 token 的唯一來源是 `docs/assets/sosol.css`。四個主頁面共用樣式，不另設色票、不載外部字型。
- 除非另有明確要求，不修改 `flight_scraper.py`、`.github/workflows/`、任何資料 JSON 或其欄位結構。
- 年曆功能不要重寫；優先只改 `docs/calendar/calendar-theme.css`。若修改年曆 HTML，必須保持與 `../SunFamilyTrip/calendar.html` 完全一致。
- 保留使用者既有未提交改動；不得自行推送或改換網站託管平台。
- 前端改動需驗證資料載入、空狀態、手機 375px 寬、選單及篩選功能。純邏輯與結構測試使用 `node --test tests/*.test.cjs`。
