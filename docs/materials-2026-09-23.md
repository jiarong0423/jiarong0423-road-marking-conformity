# 素材與方法歸類(2026-09-23)

每一張用影像辨識抓出來的圖,都附方法:圖底印方法摘要,本表列程式、重跑指令、驗證與限制。
等級:**A** 公開文件原文 ／ **B** 原解析度人眼判讀 ／ **C** 程式量測(經擾動與自我檢查)／ **D** 騎士陳述或計算推估。

## 一、影像辨識素材

| # | 素材 | 內容 | 方法(OpenCV) | 驗證 | 限制 | 程式 |
|---|---|---|---|---|---|---|
| M1 | `isolation/field-2026-09-23/cv_red_over_grates.jpg` | 新紅線畫在溝蓋上 | 格柵:灰階門檻 + 形態學閉/開 + minAreaRect + 條紋 FFT 週期性;紅線:LAB a* + 連通元件 + fitLine;圓孔:圓度 | 16/16 張中軸穿過溝蓋(距中心 1–14 cm) | 溝蓋尺寸不收斂不引用;溝蓋 7 無俯拍 | `cv_evidence.py P01 … P51` |
| M2 | 不公開（Google 街景條款禁止截圖、下載、從街景產生資料；本地留存於未版控的 `output/streetview-derived/`） | 塗銷前漸變率 4.0–5.1:1 | 外緣法 + EDLines(cv2.ximgproc)雙確認;地平線:垂直消失點與已知俯仰角各一次;夾角由消失點與 K | 換畫質、裁切讀數不動;兩地平線差約 1° | 外框 A 對車道 2.8–3.9° 未解 | `sv_taper.py`、`sv_check.py` |
| M3 | `isolation/taper-recheck/consensus_f17_f40_method.jpg` | 塗銷後 F40 約 12:1;F17 拒答 | 同 M2,地平線用垂直消失點 | 7 擾動 6 次 11.7–12.3,1 次自我檢查剔除 | 只有 F40 一張 | `consensus.py`、`horizon2.py` |
| M4 | `isolation/taper-recheck/f40_picks_method.jpg` | 舊漸變率為何飄移(診斷) | HoughLinesP + RANSAC 消失點分組 | —— | 舊方法挑到混合線組,故事原 10:1 撤回 | `draw_pick.py` |
| M5 | `isolation/field-2026-09-23/NOTES.md` §2–3 | 紅線外移約 0.60 m(溝蓋 2);新漆線寬 95–97 mm | 俯拍 LAB a* 逐列量;卡片(ID-1)同深度比對 | 卡片驗證尺 | 俯拍正射性未驗 | `topdown_redline_gap.py`、`card_vs_redline.py` |
| M6 | `results/redline_gap_F3x.json`(09-20) | 紅線外移 0.63–0.68 m | 交比 + 消失點,尺 = 紅線線寬 | 四編碼一致(endpoint 探測) | —— | `measure_redline_gap.py` |

## 二、非影像辨識素材

| # | 素材 | 內容 | 等級 |
|---|---|---|---|
| N1 | `isolation/redline_curb_labeled_P22.jpg` | ①舊紅線 ②側溝帶+溝蓋 ③新紅線 ④緣石(**人工標註**,非程式) | B |
| N2 | `isolation/glare/sun_glare.py` | 往橋頭方向全年約 86 天、11 月中–1 月底 07:00–08:00 低角度陽光在正前方 ±25° | D(計算;門檻自訂) |
| N3 | `results/solid_line_extent.json` | 實線 35 m + 槽化線 50 m;七個溝蓋 8/16/28/44/58/74/82 m | B |
| N4 | `results/merge_window.json` | 30 km/h 槽化線段 5.9 s,扣反應 2.5 s 剩 3.4 s | D(算術) |
| N5 | `evidence/field-2026-09-23/MANIFEST.csv` | 64 張,七溝蓋各俯/前/側,依時間軸定位 | B |
| N6 | 2025-06 街景 +15.7 m 路面黃色「30」 | 限速 30 | B |

## 三、法規(`docs/evidence.md`)

| 條文 | 用途 | 列 |
|---|---|---|
| 設置規則 §169 | 紅線以劃設於緣石為原則;無緣石距路面邊緣 30 cm | L2 |
| 設置規則 §183 | 劃設紅線處可免設路面邊線 → 紅線即路面外緣 | L20 |
| 市區道路及附屬工程設計標準 §2(一) | 車道 = 以標線劃定之道路部分 | L21 |
| 市區道路及附屬工程設計規範 表 4.2.7 | 30 km/h 5:1、50 km/h 16:1 | L19 |
| 公路法 §72 第四項 | 人手孔蓋回填齊平、抗滑值、3 m 直規 ±0.6 cm | L22 |
| 新北市道路挖掘作業審查原則 6.0 | 新舊路面銜接 3 m 直規 ±0.6 cm | `docs/source-ntpc-excavation-6.0.txt` |
