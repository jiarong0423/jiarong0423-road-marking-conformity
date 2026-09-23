# Road Marking Conformity

**先讀 [`docs/story-116.md`](docs/story-116.md):整個故事,白話,每個數字接來源。**


> **主軸在 [`AXIS.md`](AXIS.md)** —— 使用者重申的四點,以及每一點目前有什麼證據、
> 缺什麼。動手之前先看那一頁;不服務那四點的工作屬於 `isolation/`。
> 六個反覆犯的錯誤形狀在 [`isolation/SHAPES.md`](isolation/SHAPES.md)。

## 這個專案在講一件事

116 縣道(樹林中正路)上,一個騎士在幾秒鐘之內被三件事同時夾住:

> **捷運修路。**
> 右邊佔用又是水溝蓋,整體規劃設計不友善。
> 為什麼要提前騎中間?是避免後面道路選擇問題 —— 但前面又要上橋。
> 所以會有超長雙白線。
> 是不是又要跟車子搶,騎到水溝蓋上?

這五句是這個專案的主軸,不是背景說明。每一句都對應一個從照片量出來的
發現,而整條鏈的重點是**它們同時發生在同一個人身上**:

| 這一句 | 系統量到的 | 程式實際引用的依據 |
|---|---|---|
| 捷運修路 | 施工圍籬在行車高度佔掉畫面寬度的一段 | 新北市道路挖掘作業審查原則(**不是 §101**) |
| 右邊佔用又是水溝蓋 | 沿路的紅線 —— 它畫在緣石上還是路面上、車道是否到此為止,程式判不出來 | 設置規則 §169(原則畫緣石;無緣石時畫路面、距邊 30 cm)。照片裡它畫在齊平的混凝土帶上,而且有兩條、相距 0.63–0.68 m,見 `isolation/REDLINE.md`。**水溝蓋本程式偵測不到**,見下 |
| 前面又要上橋 | 車道在前方收窄 | 程式引的是 `L = W·V²/155`,施工之交通管制守則 p.9。**那個 155 是公式的除數。** 2026-09-22 確認:市區道路及附屬工程設計規範 113/09 修正表 4.2.7 註 2 的永久設計公式是**同一條** L = V²ΔW/155(V≤60),50 km/h 表列 16:1、不足 20 m 以 20 m 計(`docs/evidence.md` L19)。另有 **§155 路寬變更線**(L12,已持有:終點端直線 ≥ 20 m、起點端 ≥ 安全停車視距),**程式尚未用它** |
| 超長雙白線 | 雙白實線,禁止變換車道 | 設置規則 §167。**真陽性目前 0/42**,見下 |
| 跟車子搶 | 剩下的寬度不夠 | 道路交通安全規則 §101 超車須保持半公尺(**不是 §165**) |

> 這張表改了兩次,第二次是在修正第一次的過度修正。
>
> 原本第一列寫 §101、第五列寫 §165,兩者與程式對調;第三列寫「§155 漸變段」。
> 紅隊子代理指出程式裡的 155 只是 `L = W·V²/155` 的除數,這部分正確,
> 主代理據此把第三列改成「那個條文不存在」。
>
> **那句話是錯的。** `docs/markings-regulation.md` 就有
> 「§155 路寬變更線 —— 用以警告車輛駕駛人路寬縮減或車道數減少」,
> 黃色實線、線寬與間隔均一○公分、終點端直線長度至少二○公尺。
> **§155 存在,而且正好是這一列在講的事**;它只是不叫「漸變段」,
> 而且程式沒有用它。主代理當時查證了「程式裡的 155 是什麼」,
> 沒有查證「§155 這條法存不存在」,就把子代理的結論寫進文件 ——
> 這是規則 8 的實例,而且這次是**一路改到對外文件才被抓到**。

**這五句裡,系統目前不能宣稱的部分,寫在這裡而不是註腳:**

- **水溝蓋** —— 照片裡有,現場紀錄有,**本程式偵測不到**。偵測器 `_grated_cover`
  於 2026-09-21 移除,因為它在三個畫面裡找到三個週期結構,沒有一個是溝蓋。
- **雙白線** —— 它**存在**,F07 原解析度肉眼可見,距拍攝點 19–65 公尺,
  2025 年 6 月街景在同一段路的兩個門牌處都拍得到。
  而 §167 偵測器的真陽性是 **0/42**:出現過的九個判定全部畫出來看過,
  兩個屋簷、一個材質交界、一個雙黃線、一個白配黃、一個緣石。
  **這是偵測器漏掉一個確實存在的東西,不是現場沒有。**(E47)
- **橋** —— 樹林陸橋 2B-2(A),引道近端 **430 公尺**(新北市轄內橋梁基本資料)。
  那是公文事實;10 公分的線在 20 公尺外只有 14.2 像素,430 公尺外這批照片量不到。
- **前後順序** —— 「決定被推到收窄之前」沒有被量。敘事的排列是作者手排的。

這四項現在由 `assess()` 回傳在 **`site_description_not_measured`** 這個
獨立的鍵裡,與量到的 `scenario` 分開,讓沒賺到的句子無處可放。

**沒有任何一項單獨成立時是問題。** 圍籬佔一邊是常態,紅線是常態,雙白線
是常態。問題是三件事把選擇同時收掉,而做決定的時機**被推到收窄之前** ——
也就是你正忙著應付收窄的那一秒鐘之前。

所以系統的輸出不是一串條文代碼,是**一個用路人按遇到的順序會遇到什麼**,
而且只由當幀量到的東西組成:沒有量到的,一個字都不寫。

## 系統做什麼

一張街拍進去,出來的是那個地點的使用者會遇到什麼,每一項綁著管它的
台灣道路法規條文 —— 或者一個帶理由的拒答,當照片撐不起那個量測。

拒答才是重點。這個專案原本要量的東西,多數在一張未校正的手機照片上
**量不出來**,而系統會說出來而不是估一個。`docs/claims.md` 列出哪些成立、
哪些已撤回、哪些從未測過;引用這裡任何東西之前先讀它。

隔離區在 `isolation/`:那裡的程式**不在交付路徑上**,是主動搬出去的,
每一個都寫了為什麼。

## The place

116 縣道 (樹林中正路), 新北市, near 25.0027, 121.4237. A lane reduction
at a bridge approach, alongside a metro construction site. The
carriageway is bounded on the right by a kerbside red line and on the
left by a double white line, and the surface has been dug and patched
several times.

Two figures from the public accident record, both pinned in
`results/figure_registry.json`:

| A2 injury accidents within 250 m | per month |
|---|---|
| the 12 months before the works | 1.00 |
| 2026, months 1–8, during the works | 2.62 |

That is an association at one site over a short window, not a causal
claim, and `results/accidents.json` says so at more length.

![Deployment: OpenCV 5 and AWS components](docs/figures/deployment.svg)

## What the system reports

Six findings, each with its clause and its measurement:

| code | clause |
|---|---|
| `CARRIAGEWAY_OCCUPIED` | 挖掘審查原則 — hoarding standing in the running surface |
| `EDGE_NOT_CARRIAGEWAY` | 設置規則 §169 — a red line along the road edge; which surface it is on, and whether the road ends there, is not decided by the program (withdrawn 2026-09-22, `isolation/REDLINE.md`) |
| `NO_LANE_CHANGE` | §167 — a double white line forbids the change |
| `SURFACE_IN_PIECES` | 挖掘審查原則 6.0 — old and new surfacing meet, ±0.6 cm on a 3 m straightedge |
| `LANE_TOO_NARROW` | 道路交通安全規則 §101 — half a metre of clearance to overtake |
| `TAPER_TOO_STEEP` | 交通管制守則 — currently refuses on every photograph of this site |

They are composed into a narration in the order a rider meets them,
because a list of clause numbers tells an engineer which rules are in
play and does not say what the road is like to use.

**One input is not measured.** `lane_width_m` is supplied by the caller.
A photograph carries no scale, and the regulated centimetres cannot be
recovered from these captures — `docs/architecture-2026-09-21.md` works
through why, and the short answer is that deciding a 20 cm marking
against its ±6 mm tolerance needs the scale known to 3 %, while an
assumed handheld camera height gives about 17 %.

## What it refuses, and why that took a day to learn

The taper angle was this project's headline measurement until 2026-09-21,
when re-encoding one photograph at different JPEG qualities was found to
move it by more than its own size. It is withdrawn.

So is the way it was being measured. The pipeline found the road by a
local-roughness test — asphalt is smooth — and then looked for markings
inside that region. A chevron is a row of high-contrast stripes, so the
test read it as "not road" and cut it out. `docs/what-changed-2026-09-21.md`
records what that did and what five detector comparisons downstream of it
are now worth.

The angle the chevron's stripes make is measurable, and it is reported as
two numbers rather than one: **46.41° to the boundary line and 57.47° to
the road's own direction**, from four captures of one panorama. §171 says
斜四五度 and does not say relative to what. The two readings differ by
11°, against a method spread of 1.97°, so the ambiguity in the clause is
five times the precision of the instrument. The pipeline reports both and
never a single verdict.

## Running it

```sh
pip install -r requirements.txt
python3 -m pytest tests -q
```

The endpoint takes a photograph and returns the findings and the
narration:

```sh
curl -s https://3p4k7s4bx7.execute-api.ap-southeast-2.amazonaws.com | python3 -m json.tool
```

It runs as an AWS Lambda container on arm64 with
`opencv-python-headless==5.0.0.93`. `docs/deployment.md` has the rest, and
`docs/competition.md` assesses the whole entry against the competition's
own rubric, including where it is weak.

## The evidence

`evidence/field-2026-09-20/` holds 42 photographs taken at the site on
2026-09-20, at full resolution, with a manifest giving each one's
SHA-256, capture time and the EXIF focal length a measurement needs. They
are published whole because reducing them changes the answers: over the
42, a 2000 px reduction changes 17 findings and 10 taper verdicts. That
run covered the full set and is recorded in
`docs/what-changed-2026-09-21.md`, but it has no script in `scripts/` and
so is not in the registry — under this project's own rule 2 it is a
result that has not been made re-derivable. Five
carry a masked registration plate; `results/plate_redactions.json` says
which and where.

Every figure quoted anywhere in this repository is pinned by
`results/figure_registry.json` to a JSON pointer into the file that
produced it, and a pre-commit hook refuses a commit when one drifts or
when its source has been withdrawn. A number that is not in that file is
not verified, wherever else it appears.

## Reading order

| | |
|---|---|
| `docs/claims.md` | what stands, what is withdrawn, what is untested |
| `docs/what-changed-2026-09-21.md` | the defect that invalidated a day's work |
| `docs/architecture-2026-09-21.md` | the corrected design, and what it refuses to deliver |
| `docs/working-rules.md` | twelve rules, each named for the day it was broken |
| `docs/evidence.md` | the regulation verbatim, the official records, the site testimony |
| `docs/competition.md` | this entry against the rubric, weaknesses included |

## Licence

MIT. See `LICENSE`.
