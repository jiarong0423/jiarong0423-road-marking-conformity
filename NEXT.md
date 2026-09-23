# 接續點(2026-09-23 收尾)

**2026-09-23 17:05 已在 Devpost 送出**(截止前可改),報 Agentic Vision。公開 repo 最新 `9546007`;Devpost 用的 zip 與圖庫在 `output/seven-drain-grates-submission.zip`、`output/devpost_gallery/`,草稿 `output/devpost_submission.md`。Agentic 證據:`docs/figures/agent-workflow.png`、技術報告 §8(20 張評估 20/20;106 張全量未跑完,可逐張重跑 `isolation/agentic/evaluate.py`)。

**比賽交付已齊**:公開 repo `jiarong0423/jiarong0423-road-marking-conformity`(英文 README/故事/技術報告/素材總表/圖)、影片 https://youtu.be/jNofo20hvyY (3:27)、AWS v13 上線。
- AWS:v13 含通行碼閘門(`~/road116_access_token.txt`,不進 repo,提交表單給評審)、3008 MB(帳號上限)、限速 1/s burst 3、Function URL 已刪、日誌 14 天、$5 預算警報。重跑 `MEMORY=3008 ./aws/harden.sh <email>`,冪等。
- 未解:記憶體上限 3008 → 原圖線上逾時,新量測雲端跑不出來;要 AWS Support 提額(未申請)。已寫信給 competition@opencv.org 詢問(2026-09-23 15:45),待回覆。
- 公開 repo 更新方式:`git commit-tree HEAD^{tree} -p public-release` → 推 `public` remote 的 main,**不推本地完整歷史**。推前掃個人路徑/密鑰/街景圖。
- 街景衍生圖不公開(Google 條款),本地 `output/streetview-derived/`;中文原稿在 `output/zh-originals/`。

- **結案盤點(2026-09-23 17:15)**:本地、GitHub、AWS 三方一致;212 測試過、73 數字對上、106 張證據 sha256 一致。無背景程序、無測試容器、預覽伺服器已停。本地的 Devpost 上傳檔、中文原稿、街景衍生圖、`video/out/` 已於 17:20 刪除(使用者指示);要重做:影片 `video/make_video.py`、街景圖 `isolation/overlay-2025/sv_taper.py`、中文版在 git 歷史 `3a00a5a` 之前。Docker 有 v1–v13 映像約 5 GB,可 `docker image prune` 清。`/etc/hosts` 的三行 googleapis 已被使用者註解掉(為了 Vertex 配音),若別的專案推 Google Sheet 出問題先看這裡。

---

# 接續點(2026-09-22 夜,/clear 前盤點)

開場先讀:`AXIS.md`(主軸+主訴)→ `docs/story-116.md`(故事)→ 本檔。錯誤紀錄只在 `isolation/`,不進報告。

## 已站住(不用再動)

| 數字 | 值 | 檔 |
|---|---|---|
| 紅線外移 | 0.63–0.68 m(F30/31/32) | `results/redline_gap_F3x.json` |
| 漸變率 | ~10:1(F17 6.2°、F40 4.8°)vs 表 4.2.7 50 km/h 16:1 | `results/taper_phone.json`;`docs/evidence.md` L19 |
| 實線起點→橋頭 | 85 m;實線 35 m + 槽化線 50 m;比 2024-09 提早約 40 m | `results/solid_line_extent.json` |
| 七個溝蓋 | 8/16/28/44/58/74/82 m(偵測 5 + 人眼 2) | 同上 `#/drain_covers` |
| 併道秒數 | 50 km/h 剩 1.1 s;30 km/h 3.4 s | `results/merge_window.json` |
| 法條 | §155/§157(平交道,非縮減)/§188-1/§56/§60/設計標準 §11/表 4.2.6/4.2.7 逐字 | `docs/evidence.md` L12–L19 |

## 缺口(依優先序)

1. **2026-09-23 已拍 64 張,位置已排**(`evidence/field-2026-09-23/README.md`、`MANIFEST.csv`:七組對上 8/16/28/44/58/74/82 m)。
   每個溝蓋俯/前/側三種都有(側拍像前拍,只差相機高度,見 `view` 欄);沒有 GPS。
   `measure_redline_gap.py` 對 64 張全部拒答(近拍沒有垂直結構、舊線不在畫面下方),要另寫俯拍版。下一步:紅線外移用 P08–P10 重量、格柵偵測跑俯拍 16 張(原解析度)、P55–P61 卡片當絕對尺。
   原本這條:**明早 06:00–07:30 現場拍攝**(行事曆已排;清單 https://claude.ai/artifact/VTs64piazs2NpNyZ2Ak2iP,雲端硬碟有離線版)。
   回來後:`python3 -B scripts/intake_field.py <資料夾>` → 可用幀 → 跑 `measure_redline_gap.py --frame N`、格柵偵測(原始解析度,不縮圖)、溝蓋落差(側拍+直尺,**還沒有腳本**)。
   點位:ArtifactData 讀 artifact `VTs64piazs2NpNyZ2Ak2iP` 的 collection `points`。
2. **endpoint 已接(2026-09-23,本地,未部署)**:`assess()` 多了 `red_line_gap`、`taper_table_4_2_7`(與舊集成並跑,使用者決定)、每次都附 `site_116_not_measured_from_this_photograph`;`actions.py` 加三份文件申請。量測核心搬到 `src/marking/phone.py`,腳本輸出逐位元不變。
   **部署卡兩件,都要使用者決定**:(a) 新量測只在原解析度站得住(2000 px 全拒答),原檔 5–10 MB > 3 MB 上限(Lambda 同步 6 MB);(b) 原解析度 assess 本機 35–38 s > 30 s。
   **故事數字要重驗**:`taper_phone` 的 10:1 對編碼不穩 —— F40 原檔 11.9,品質 97 重編一次 23.2(跨過 16:1),F17 重編即拒答。endpoint 已加四編碼一致才回報的閘;故事裡的 10:1 還沒改,待使用者決定。
   原本這條:**endpoint 沒接新東西**:`assess()`/`aws/handler.py` 還跑舊四偵測器(85 s vs 30 s 逾時,G14)。要把 redline gap、taper、extent、merge window 接成輸出 + `actions.py` 的 REQUEST_DOCUMENT。**這是比賽最該做的一件。**
3. **2026-09-23 公開 repo**:`jiarong0423/jiarong0423-road-marking-conformity`(PUBLIC),單一 commit `e781c56` = 本地 `c2310ba` 的樹;舊 PRIVATE repo 使用者已刪。之後更新用 `git commit-tree` 疊在 public-release 上再推 `public` remote,**不推本地完整歷史**。街景衍生圖不公開(Google 條款),本地在 `output/streetview-derived/`。
   雲端仍 v11;v12 已建置測試,部署三指令待使用者在終端機執行。
4. 影片沒拍;架構圖是上一版(缺兩把尺/消失點/拒答那條線);評分權重未查。
5. 斜紋角度自動算:五種抽線 + 結構張量第一版都不收斂(`isolation/DETECTORS.md` 補四~七);外部建議 A/C/Se 2000 在 `isolation/EXTERNAL_STRIPE.md`。**不是故事需要的**,有空再做;槽化線不再進場拍。
6. 三份文件要申請(故事結尾列了):改繪核定函及劃設圖說、許可 1140874494 交維計畫、側溝竣工圖與蓋板檢驗報告。
7. 小的:F24 紅線拒答原因未究;`results/tolerance.json` 用臺北市 02898 不拘束新北;G25 跨種子離散;G39 引用檢查不含 docs/。

## 重跑
- 全套測試:`python3 -B -m pytest -q -p no:cacheprovider`(198 passed;**不要接管線,退出碼會被吃**)
- 數字對帳:`python3 -B scripts/check_figures.py`(73 published, 14 archive-only)
