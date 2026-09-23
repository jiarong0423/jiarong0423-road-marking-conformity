# 缺口佇列

2026-09-22 建立。來源:`isolation/ERRORS.md` E01–E20,加上尚未驗證的子代理報告項。

**排序原則:餵給越多下游的越前面。** 上游沒修之前,下游的數字量了也不能用。

**規則**:一項只有在「修好 + 自己重跑 + 驗證者獨立確認 + 監督者沒有推翻」四項都成立
之後才標 `DONE`。只修不驗的標 `修了未驗`,不算完成。

---

## 佇列重排,2026-09-22:原本的排序選錯了軸

監督子代理指出、主代理逐項自查屬實:**G01–G16 有十項在服務漸變段/§171 那條線**,
而那條線的頭條數字(46.41°/57.47°)**不是從這 42 張照片來的**
——`results/chevron_angle.json` 寫明是 2025-06 的一張 Street View 全景重投影四次——
**而且已經 `withdrawn`**。E10 又確認雪佛龍在那之後重畫了。

使用者那五句話裡,系統唯一非答對不可的是「**超長雙白線**」,
而 §167 目前 **0/42,九個判定全是偽陽性**。它原本排在第五。

**新的第一項是 G00,它不在原本的佇列裡。**

---

## G00(新,最高)E21 主軸那條因果鏈是寫死的中文

`_scenario` 用一段固定文字宣稱「為了前方上橋才畫的、一路封到引道、
必須在收窄之前決定完、那 1 秒鐘」,以及「你騎的是排水溝上面那條」——
**橋沒量、順序沒量、1 秒是裸常數、水溝蓋的偵測器在 2026-09-21 就被移除了**。
而觸發整段的布林值真陽性是 0/42。

`_scenario` 的 docstring 寫著 "Nothing is narrated that was not detected."

**驗收條件**:敘事裡的每一個子句,要嘛指向一個當幀量到的值並把數字寫出來,
要嘛明確標示為「未量測的現場描述」。**不准有第三類。**
並且 `verified/README.md` 的 V02 必須先撤下。

---

## 封鎖中:在這三項修完之前,不得引用任何全母體計數

| # | 項目 | 為什麼擋著全部 | 驗收條件 |
|---|---|---|---|
| **G01** | **E13** `ROI_FRAC_MAX=0.87` 閘門結構性失效 | 唯一擋住「這不是道路照片」的東西。新橫帶上限 0.600,永遠到不了 0.87;另一半判 `is None` 而非「空遮罩」,於是零像素區域被回報 `carriageway_found: true` | 12 張雜訊幀 **12/12 拒答**;`pytest tests/` 全綠 |
| **G02** | **E15(已修正描述)** endpoint 無條件相信呼叫端給的視角,而 `cv2.imdecode` 把 EXIF 丟了 | **不是寫死 60** —— 那個說法我沒查證就接受了,是規則 8 的實例。缺陷是伺服器手上有能定案的檔案卻讀不到,而本專案每次都傳 60,對 42 張全錯 | handler 在 decode **之前**從 bytes 讀 EXIF 並與呼叫端對帳;不合就拒答或以檔案為準。**注意**:改 fov 會讓所有在 60 下校準的常數(corridor 1–20°、`tol_deg=1.2`、`reach_frac=0.085`)失效,必須一併重新推導,否則是守則 5 第三次 |
| **G03**(降級,服務已撤回的量測) | **E14** §171 資格篩選是死的 | `scored` 算了只用來判空,`pick = max(tried, …)` 排的是全部候選。§171 是本專案回答「哪條線是邊界」的**全部依據**,被降級成 0.25 加分項 | 排序改用 `scored`;**要有一個測試 import `sequential.py`**(目前零個);對比修前修後在 42 張上的差異並落檔 |

---

## 待修

| # | 項目 | 根因 | 驗收條件 |
|---|---|---|---|
| **G04** | **E16** 敘事偷渡 3 公尺車道寬 | `secs = (3.0/rate)/…` 的 `3.0` 是比例尺,直接牴觸「照片沒有比例尺」這個核心主張;來源 `results/reaction.json` 已 `withdrawn` | 要嘛移除那一句,要嘛把 `lane_width_m` 變成呼叫端**明示**的輸入並在敘事裡說明「這句依賴一個你提供的假設」;要有測試 |
| **G05** | **E05/M05** §167 仍然把緣石配成雙白線 | 兩條線都不是漆時,「兩側同材質」和 b\* 都會過 | 加「兩條都必須是漆」的判準;**每一個判定都要畫出來看過**才計數 |
| **G06** | **E18** `_works_hoarding` 收 `roi` 沒用 | 簽章宣稱看區域,程式沒有 | 要嘛用它、要嘛移除參數並說明;有測試 |
| **G07** | **E19** `test_every_encoding_is_attempted` 是恆等式 | 斷言自己等於自己;名字承諾的 `attempted` 沒被斷言 | 改成斷言 `attempted`;用突變證明它會失敗 |
| **G08** | **M11** 另外兩個空測試 | `test_noise_frame_cannot_measure` 接受 `INDETERMINATE`,等於允許對純雜訊做出量測;`test_hook_chain` 兩項在 hook 不存在時 skip → 刪掉 hook 反而全綠 | 各自用突變證明會失敗 |
| **G09** | **M06** 沒有測試的函式 | `sequential.py` **七個函式全部沒有測試**;`gate2` 四個;`situation` 四個;`extract.road_region`、`markings` | 先補 `sequential.py`(G03 需要),其餘列表逐項 |
| **G10** | **M08** 重跑產出腳本會抹掉 `withdrawn` 標記 | 標記是手寫進 JSON 的,24/28 腳本沒有 `--write` 護欄,登錄表印出的 regenerate 指令就是解除檢查的指令 | 產出腳本要能發出 `withdrawn`,或 `check_figures` 改從獨立清單讀 |
| **G11** | **M12** 8 個登錄圖表在乾淨 clone 上跑不起來 | `pixel_budget.py` 讀 `data/`(gitignored),`measure_chevron.py` 讀 `output/api/`(gitignored),`erasure_ratio.py` 寫死暫存路徑 | 改讀 `evidence/`;登錄的 regenerate 指令實際跑得起來 |
| **G12** | **M12b** `pixel_budget` 用 F01 一張的相機算 42 張的預算 | 3 張是 f35=46,對它們 `red_line_px_at_20m` 是 27.2 px 不是 14.2 px | 分組報告或報範圍 |
| **G13** | **M15** `taper_with_hatching` 的評分是循環的 | `evidence` 與挑選候選的目標是同一個量,與成員數相關 0.936 | 換一個不由生成器控制的判準,或明說它是循環的並停止當作證據 |
| **G14** | **M16** `markings()` 全解析度 26 秒 → 30 秒 API 逾時 | `assess()` 為了餵 `_double_white` 在全解析度跑一次,集成卻只用 ≤1800 px | 量出各段耗時;決定 §167 要不要也在集成尺寸上跑 |
| **G15** | **M13** 文件裡的數字與來源對不上 | README 說「twelve rules」實為 14;「refuses on every photograph」已非事實;`aws/handler.py` 說「measures in the bird's eye plane」而程式相反 | 逐條對帳 |
| **G16** | **M10** `draw.overlay` 沒有 `TAPER_TOO_STEEP` 的畫法 | E11 說所有發現都來自畫出來看,而漸變段**是唯一沒被畫過的** | 補畫法;把 6 張斷言幀畫出來逐張看 |

---

## 監督者建議直接丟掉的

**G13**(循環評分)—— 結論應該是停止主張漸變段,不是換一個判準。
**G16**(把 `TAPER_TOO_STEEP` 畫出來)—— 畫圖的力氣要花在 §167 那九個偽陽性上。
**G12**(3 張的像素預算分組)—— 論點已經成立。
**G09** 限縮到三個偵測器,不為 `sequential.py` 七個函式補測試。

## 執行順序(定版)

`G00 → G05 → G01 → G06 → G14 → G04 → G07/G08 → 其餘`

## 狀態(驗證者維護。只有驗證者親自重跑過驗收條件才寫 DONE)

最後更新 2026-09-22,驗證者。基準線 `b1e0d93`,現行量測 `0401f72` / `68708d0`。

| # | 狀態 | 驗證者親自重跑 | 備註 |
|---|---|---|---|
| **G00** | **`DONE`** | `0401f72` 12/12、`68708d0` 153 passed | 敘事拆成 `scenario` / `site_description_not_measured`,V02 已撤回。**四個突變全部被殺**(下節)。殘留見 E42.2:`CENTRE_LINE_SOLID` 仍無敘事分支 |
| **G01** | **`DONE`** | `0401f72`:雜訊 **12/12**、真實 **0/42 誤擋**、**0/42 崩潰** | 強化後三項條件全中。閘門程式自 `0401f72` 起未變動,數字沿用。**但註解宣稱的範圍不成立,見 E41** |
| G02 | `TODO` | — | |
| G03 | `TODO` | — | |
| G04–G16 | `TODO` | — | G14 的數字要改:不是 26 秒,是 194 秒(E45) |
| G17 | `TODO` | — | `_kerbside_red` 抓到水馬,未修 |
| G18 | `DONE`(記錄者已驗) | — | 見下節 |
| G19 | 部分 | — | 見下節 |
| G20 | `TODO` | — | |
| **新** | `TODO` | E40 / E41 / E42 / E45 | 驗證者第四輪找到,見 `ERRORS.md` |

### 未結的,依嚴重度

1. **E40** `carriageway_found` 是 `numpy.bool`,`json.dumps` 在 handler 的 try 之外
   → 42/42 真實照片都會是**無訊息的 500**。這是目前唯一會讓 endpoint 整個不能用的一條。
2. **E45** `assess()` 194 秒對 30 秒契約;且 F30 的 `SURFACE_IN_PIECES` 被新規則拿掉,
   全母體影響**尚未量**(未 commit,趁現在)。
3. **E41** 閘門分開的是飽和度不是路面:灰牆、灰階雜訊都拿 0.6000 過閘。
4. **E42** `assess()` 兩條路徑回傳不同鍵集;`CENTRE_LINE_SOLID` 畫不出、不入敘事;
   `ROI_FRAC_MAX` 死常數 + 五份文件仍描述它,其中 `docs/submission.md` 的查核指令仍會成功。

---

## G00 / G01 驗收,驗證者獨立重跑,2026-09-22

### 1. 12 張雜訊幀(`0401f72`,強化後的三項條件)

`findings == []` **且** `scenario == []` **且** `carriageway_found is False`。

```
seed      shape  roi_frac  cw_found  findings  scenario  site_desc                  state
   0    600x800    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   1   900x1200    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   2  1050x1400    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   3  1400x1050    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   4    600x800    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   5   900x1200    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   6  1050x1400    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   7  1400x1050    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   8    600x800    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
   9   900x1200    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
  10  1050x1400    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH
  11  1400x1050    0.0000     False         0         0          0  NOT_A_ROAD_PHOTOGRAPH

PART A: 12/12 satisfy findings==[] and scenario==[] and carriageway_found is False
```

基準線是 10/12,而且十二張**每一張**都出兩項發現加一整段敘事(E22)。現在 0。

### 2. 42 張真實照片:新閘門有沒有誤擋(這一半比較重要)

```
roi_frac range over 42: 0.5550 - 0.6001
wrongly refused by the new gate: 0/42 []
tightest margin: F11 at roi_frac 0.5550, which is 0.2550 above MIN_ROAD_FRAC (1.85x the threshold)
assess() RAISED on: 0/42 []
```

逐幀 `roi_frac`(全部 PASS):

| F01 .5760 | F02 .5685 | F03 .5855 | F04 .5561 | F05 .5902 | F06 .5575 | F07 .5766 |
|---|---|---|---|---|---|---|
| F08 .5852 | F09 .5782 | F10 .5643 | **F11 .5550** | F12 .5783 | F13 .5882 | F14 .5778 |
| F15 .5890 | F16 .5888 | F17 .5956 | F18 .5966 | F19 .5978 | F20 .6000 | F21 .5952 |
| F22 .5805 | F23 .5938 | F24 .5768 | F25 .5942 | F26 .5804 | F27 .5730 | F28 .5779 |
| F29 .5686 | F30 .5907 | F31 .5890 | F32 .5887 | F33 .5899 | F34 .5904 | F35 .5944 |
| F36 .6001 | F37 .5939 | F38 .5864 | F39 .5841 | F40 .5992 | F41 .5819 | F42 .5784 |

**最接近門檻的是 F11,0.5550,餘裕 0.2550,是門檻的 1.85 倍。**
上緣 F36 的 0.6001 貼著純橫帶的結構上限 0.600(E20),所以這個分佈的寬度
**不是量出來的,是幾何決定的**——這正是 E41 要說的事。

**`assess()` RAISED 0/42**:`0401f72` 之前這裡是 25/42 `AttributeError`(E32),
現在零。逐幀發現數 0–3 都有,沒有一張被閘門吃掉。

### 3. 全套測試與 `check_figures`

| commit | 測試 | check_figures |
|---|---|---|
| `b1e0d93`(基準線) | **1 failed, 138 passed** | 24 figures, exit 0 |
| `e119b7f` | 139 passed(**0 個新測試**) | 24 figures, exit 0 |
| `0401f72` | **148 passed**(+9) | 24 figures, exit 0 |
| `68708d0` + 未 commit 的 `M situation.py` | **153 passed** in 133.66s | **27 figures**, exit 0 |

基準線唯一的紅燈 `test_a_frame_that_is_all_carriageway_is_refused` 已綠。無新紅燈。

### 4. 突變驗證,驗證者獨立重跑(不採信主代理的結果)

在 `/tmp` 的隔離副本上做,**沒有碰正式 repo**(守則:隔離測試不得 `mv` 正式檔)。
`R` 是未突變的還原對照,與 HEAD 逐位元相同。

| 突變 | 結果 | 被殺的測試 |
|---|---|---|
| **R** 還原對照 | **9 passed** | — |
| **A** `len(findings)` → `len(steps)` | **3 failed, 6 passed** | 三個計數測試全部 |
| **B** `side` → 寫死 `"右"` | **1 failed, 8 passed** | `...[box0-左]` |
| **C** 拿掉 §165 分支 | **1 failed, 8 passed** | `..._double_yellow_line_is_not_reported_as_no_lane_change` |
| **D** `px` 當 dict 讀(`e119b7f` 的 bug) | **4 failed, 5 passed** | 三個 `side` 參數化 + `..._real_detector_shape_does_not_raise` |

**四個突變全部被殺。** 與主代理回報的「各自 1 failed」略有出入:
A 是 3 failed、D 是 4 failed。結論相同,數字以本節為準。

**還有沒有第三個空測試 —— 沒有。** 九個測試裡,上表殺掉八個;
第九個 `test_a_double_white_line_still_is_no_lane_change` 四個突變都殺不掉,
因為它是**正向對照**(守則 6),職責本來就不是擋這四個。
驗證者另外做了三個針對它自己標的的突變,**三個都殺得掉**:

| 額外突變 | 結果 |
|---|---|
| **E** `elif dw:` → `elif False:`(§167 發現根本不發) | **1 failed** |
| **F** `if dw and section=="165":` → `if dw:`(白線也報成 §165) | **1 failed** |
| **G** §167 的 basis 拿掉條號 | **1 failed** |

所以九個測試**沒有一個是空的**。

**另外,計數測試能不能分辨 findings 與 steps,是實測過的**,不是假設:

```
1 finding  -> 2 steps    DISTINGUISHES
2 findings -> 4 steps    DISTINGUISHES
3 findings -> 5 steps    DISTINGUISHES
```

三組輸入的兩個數字都不相等,所以 A 突變必然改變輸出。

### 5. 反向檢查:還有誰讀了改掉的東西

已知兩項(handler 的 `returns`、`draw.py` 不畫 `site_description_not_measured`)
**在 `68708d0` 上已修**,驗證者確認。另外找到四項,其中兩項也已修:

| 項目 | `0401f72` | `68708d0` |
|---|---|---|
| `CENTRE_LINE_SOLID` 不在 handler `finding_codes` | 缺 | **已修** |
| `NOT_A_ROAD_PHOTOGRAPH` 不在 handler 自述 | 缺 | **已修** |
| `CENTRE_LINE_SOLID` 不在 `draw.py` 的 `CLAUSE`/`COLOUR`,`_scenario` 也沒有分支 | 缺 | **仍缺**(E42.2) |
| `assess()` 兩條路徑回傳不同鍵集 | 是 | **仍是**(E42.1) |
| `ROI_FRAC_MAX` 死常數 + 五份文件仍描述它 | 是 | **仍是**(E42.3) |

再加兩項是驗證者自己跑出來的,不在主代理的清單上:
**E40**(`numpy.bool` → handler try 之外的 `json.dumps` TypeError)
和 **E45**(194 秒 vs 30 秒契約)。

---

## 驗證者基準線,2026-09-22(修復動工之前)

commit `b1e0d93`;`git status --short` = `M isolation/ERRORS.md`、`?? isolation/GAP_QUEUE.md`
(`src/`、`tests/`、`scripts/` 皆乾淨,所以下面的數字量的是 `b1e0d93` 本身)。

### 全套測試

```
$ /opt/anaconda3/bin/python3 -m pytest tests/ -q
1 failed, 138 passed in 282.15s (0:04:42)

FAILED tests/test_taper_ensemble.py::test_a_frame_that_is_all_carriageway_is_refused
E       AssertionError: only 10/12 noise frames were refused
E       assert 10 == 12
```

唯一的紅燈,與 E12 記的同一個。139 項,138 過。

### `check_figures.py`

```
$ /opt/anaconda3/bin/python3 scripts/check_figures.py
24 published figures match their sources
（exit 0）
```

### G01 驗收條件:12 張雜訊幀走 `situation.assess()`

幀的造法與 `test_a_frame_that_is_all_carriageway_is_refused` 完全相同
(`default_rng(seed)`,尺寸依 `seed % 4` 取
`[(600,800),(900,1200),(1050,1400),(1400,1050)]`)。

| seed | 尺寸 | `roi is None` | `roi` 像素佔比 | `taper.state` | `carriageway_found` | `findings` |
|---|---|---|---|---|---|---|
| 0 | 600x800 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 1 | 900x1200 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 2 | 1050x1400 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 3 | 1400x1050 | False | **0.0000** | **INDETERMINATE** | **True** | **2** |
| 4 | 600x800 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 5 | 900x1200 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 6 | 1050x1400 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 7 | 1400x1050 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 8 | 600x800 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 9 | 900x1200 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 10 | 1050x1400 | False | **0.0000** | CANNOT_MEASURE | **True** | **2** |
| 11 | 1400x1050 | False | **0.0000** | **INDETERMINATE** | **True** | **2** |

**拒答 10/12。** 與測試的紅燈一致(同樣是 seed 3 和 11 漏掉,兩張都是直幅
1400x1050)。

三件事同時被這張表釘住:

1. **閘門的兩半都沒有觸發過一次。** `roi is None` 十二次都是 False,
   `roi_frac` 十二次都是 **0.0000** —— 離 `ROI_FRAC_MAX = 0.87` 不能再遠。
   E13 說的「永遠不會觸發」是實測。
2. **`road_region()` 在雜訊上回的是零像素遮罩,不是 None。** 十二次全部。
   `carriageway_found: True` 因此十二次全部為真,而底下是零個像素。
3. **`assess()` 對純雜訊各出兩項發現和一整段敘事。** 這是新的,見 E22。

### G01 驗收條件要補

現在寫的「12 張雜訊幀 12/12 拒答」只讀得到 `taper.state`。照這個字面,
把 seed 3、11 修成 CANNOT_MEASURE 就算過,而 `assess()` 仍然會對這十二張
各回兩項發現、`carriageway_found: True`、和一段叫人往左看往右看的敘事。

**建議改成(三項全中才算過)**:

1. 12/12 `taper.state == "CANNOT_MEASURE"`;
2. 12/12 `assess()["findings"] == []`;
3. 12/12 `carriageway_found` 為 False,或那個鍵改成回報**非空**遮罩。

並且要同時證明**真實照片沒有被這個條件擋掉** —— 42 張跑 `assess()`,
`carriageway_found` 與發現數與修前一致(守則 6、守則 10)。
只報拒答不報誤拒,這個閘門等於沒被評估過。


---

## 第三輪新增(紅隊,2026-09-22)

| # | 項目 | 錯誤編號 | 狀態 |
|---|---|---|---|
| **G17** | `_kerbside_red` 把橘黃色水馬與三角錐抓成 §169 紅線 | E27 | TODO |
| **G18** | 「未量測」容器在 `draw.py`、`handler.py` 契約、測試三處都不存在 | E29 | **DONE** 2026-09-22(記錄者重跑,見下) |
| **G19** | 我加進敘事的 430 m / 355.6 m / 31 s 不在圖表登錄裡 | E30 | **部分完成**(見下) |
| **G20** | 七個仍無來源的子句(0.8 秒、2.5 秒、速限當車速、視距、本來是路、車流、一台車) | E31 | TODO |

已修待驗:**G00**、**G01**、E25、E26、E27(左右部分)、E28 → 驗證者處理中。

---

## 第四輪新增(記錄者自行重跑,2026-09-22)

| # | 項目 | 錯誤編號 | 狀態 |
|---|---|---|---|
| **G21** | `assess()` 的通過分支不回傳 `roi_frac`,只有拒答分支回 | E34 | TODO |
| **G22** | `control_group.json` 把已撤回的 0.202 抄成常數 14.9,而它自己沒有 `withdrawn` 標記,`check_figures` 第三條規則看不見 | E35 | TODO |
| **G23** | `assess()` 不是決定性的:`_surface_types` 的 `cv2.kmeans` 沒有種子,同一批位元組兩次跑出不同答案 | E43 | 主代理修復中(`surface_types_stable()`),記錄者未驗 |
| **G24** | 記錄者的紀錄被別人的 commit 夾帶(守則 12 第四、五次) | E44 | **第六次:2026-09-22,`docs/evidence-index.md` 還在寫、記錄者尚未交付,就被 `1643b93` 夾帶進去。規則已存在,缺的是執行 —— `git add` 要列檔名,不要 `-A`/`.`** |
| **G25** | 定種子之後,`surface_types_stable(runs=1)` 的第二個回傳值恆為 `True`,那道「不穩就不報數」的閘門在交付路徑上關掉了 | ER01 | TODO |
| **G26** | `check_figures.py` 只檢查「在場的項目對不對」,不檢查「該在的項目還在不在」;登錄項被整檔覆寫刪掉,檢查全綠 | ER02 | TODO |

**G26 驗收條件**:刪掉任何一個登錄項,`check_figures.py` 要紅,
或要求該次 commit 明說並寫進 `withdrawn_figures`。
**用突變證明**:真的刪一項、跑檢查、看它失敗。
（實例:記錄者加的 12 個 `assess_*` 在 2026-09-22 被整檔覆寫刪光,
`check_figures` 從 39 項掉到 35 項,**exit code 兩次都是 0**。）

**G25 驗收條件**(擇一,不得兩個都不做):
(a) 刪掉 `st_stable`、`and st_stable`、以及 `not_checked` 那一句,
    在註解寫明「種子取代了投票」;或
(b) 讓跨種子散布**離線量一次並落檔**(docstring 已經承諾
    「measured once offline and recorded」,那個檔目前不存在),
    回應改為引用該檔。
兩者都要有一個**突變殺得死**的測試:改掉分支,測試要紅。

**G23 進度(記錄者自查,2026-09-22)**:驗收條件第 1 項**已過** ——
`surface_types_stable()` 對 42 張各呼叫兩次,**0/42 不一致**,
母體計數兩次都是 **20/42**(`<scratch>/gate42.py`,輸出見 E46)。
第 2 項(整個 `assess()` 跑兩次逐張相同)**尚未有人做過**,指令是:

```
/opt/anaconda3/bin/python3 scripts/assess_field.py --out A.json
/opt/anaconda3/bin/python3 scripts/assess_field.py --out B.json
# 然後逐張比對 photographs[].findings[].measured,不是只比 totals ——
# E43 就是 totals 相同而 F18 不同
```

第 3 項(`route_refusal.py` 那句 "same bytes in, same verdict out")
**仍未處理**:定種子之後那句話有機會成立,但還沒有人證明它成立。

**G23 驗收條件**(缺一不可):
1. 同一個 process 內連續呼叫 N 次,42 張**全部**回同一個值,或那一張
   **不出 `SURFACE_IN_PIECES`** 並在 `not_checked` 裡說明;
2. **整個 42 張跑兩次,兩份 JSON 逐張相同**(不只 `totals` 相同 ——
   E43 就是 `totals` 相同而 F18 不同);
3. `isolation/scripts/route_refusal.py` 那句
   「same bytes in, same verdict out」要嘛成立,要嘛改掉。
   一句被推翻的設計理由留在原地,比沒有那句還糟。

**這一項擋著任何「N/42」的引用。** 在 42 張跑兩次逐張相同之前,
`SURFACE_IN_PIECES` 的母體計數(記錄者兩次都量到 34/42)是**某一次的觀測**,
不是這個偵測器的性質。

**G21 驗收條件**:`assess()` 的兩條 return 路徑都帶 `roi_frac`;
`scripts/assess_field.py` 隨即移除 `roi_frac_recomputed` 這個繞道欄位,
42 張重跑的值與繞道值逐張相同。
**這一項擋著 G01** —— G01 驗收條件第 3 項要用 `assess()` 的輸出證明
真實照片沒有被誤拒,而那個輸出裡沒有它要比的數字。

**G22 驗收條件**(兩選一,不得都不做):
(a) `scripts/control_group.py` 在 `TAPER` 來源被撤回期間,
於 `results/control_group.json` 寫出自己的 `withdrawn` 標記;或
(b) `check_figures.py` 改為沿著「哪個腳本抄了哪個撤回值」追一層。
在此之前,`taper_m` / `erased_share` / `time_available_s` / `day`
**不得登錄**,理由見 E35。

---

## G18 驗收:記錄者重跑,2026-09-22

E29 要求三個出口同步,逐項查證:

1. **`src/marking/draw.py`** —— 有。`panel()` 第 295–318 行畫
   `site_description_not_measured`,琥珀色標題
   `NOT measured - site description, from the record`,
   底部圖例 `teal = measured in this frame; amber = not measured`。
2. **`aws/handler.py` 自述契約** —— 有。`returns` 區塊第 84–90 行
   列出 `site_description_not_measured`。
3. **測試,而且非恆真** —— 有,且**突變殺得死**。

突變驗證(用 `cp -R` 複製到暫存目錄改,**沒有動正式檔**):

```
$ cp -R src tests <scratch>/g18mut/
$ /opt/anaconda3/bin/python3 -m pytest <scratch>/g18mut/tests/test_draw.py -q -k unmeasured_block
1 passed, 7 deselected in 0.78s

# 突變:把 site 改成永遠是空的(G18 之前的行為)
#   site = []   # MUTATION: pre-G18 behaviour
$ /opt/anaconda3/bin/python3 -m pytest tests/test_draw.py -q -k unmeasured_block
E       assert 0 > 0
FAILED tests/test_draw.py::test_the_panel_draws_the_unmeasured_block
1 failed, 7 deselected in 1.04s
```

四項成立(修好、自己重跑、突變證明非恆真、三個出口逐一查證),標 `DONE`。

---

## G19 驗收:登錄了三個,第四個登錄不了,理由寫在這裡

**已登錄**(`results/figure_registry.json`,`check_figures.py` 現在 27 項全過):

| id | 值 | 來源 |
|---|---|---|
| `bridge_structure_id` | `樹林陸橋2B-2(A)` | `results/control_group.json#/sight_line/structure` |
| `bridge_near_end_m` | `430` | `#/sight_line/near_end_m` |
| `bridge_length_m` | `355.6` | `#/sight_line/length_m` |

重跑指令 `/opt/anaconda3/bin/python3 scripts/control_group.py` 逐位元組重現
該檔(已驗,見 E35)。三項的 `convention` 都寫明這是**橋梁公文的轉錄,
不是本專案的量測**,`bridge_near_end_m` 另外寫明 E30 的第二個問題:
「距**此** 430 公尺」的「此」沒有定義,V08 說這 42 張沒有 GPS。

**登錄不了的:`31 秒`**(`src/marking/situation.py:479`
「時速 50 公里跑 430 公尺是 31 秒」)。

沒有任何腳本產出它。它是 `430 / (50/3.6) = 30.96` 這個算式的結果,
而 `50` 是**速限不是車速**(E31 已記)。
依登錄表自己的規則「a number that is not here is not verified」,
**它現在是一個未登錄的數字**,要嘛由某個腳本產出並登錄,
要嘛從敘事裡拿掉。登錄一個沒有腳本能重跑的值,只是把未驗證改寫成看起來已驗證。

**所以 G19 是部分完成**,剩下的併入 G20(裸常數那一類)。

---

## 第五輪:清冊的四個缺口接進佇列(記錄者,2026-09-22)

**先修一個編號碰撞。** `docs/evidence-ledger-2026-09-22.md` 點名的四個缺口,
原本被追加在本檔最末,用的是 **G21–G24**,而本檔上面已經有一組
G21(`roi_frac`)/ G22(`control_group`)/ G23(決定性)/ G24(commit 夾帶)。
同一份佇列裡兩個 G23 指兩件事,任何一句「G23 修好了」都不成立。
**四項改編為 G26–G29,舊的 G21–G25 維持原義,G21–G24 這四個號碼不再指清冊那四件事。**

| # | 項目 | 錯誤編號 | 狀態 |
|---|---|---|---|
| **G26**(原誤編 G21) | 用槽化線間距當尺規量剩餘可騎乘寬度 | E46 | TODO — 想法成立,兩次量測都是雜訊的中位數。需要亮段過濾、多剖面共識、明確的失敗條件,以及用 §171 第二個比值(20:15=1.333)做獨立驗收。**取樣要垂直於斜紋**;另見 G31,量測範圍的起訖與清冊寫的不同 |
| **G27**(原誤編 G22) | 那條「超長白線」是 §171 外圍單實線還是 §167 雙白實線 | — | TODO — **題目本身要先改**,見 G31 |
| **G28**(原誤編 G23) | 「一出口就縮減」的空間關係完全沒量 | — | TODO — 敘事順序是手排的。拍攝順序=行進方向已確認,所以序位可表達 |
| **G29**(原誤編 G24) | 去拿交通局的交通維持計畫 | — | TODO — A 級,同時定案第三、四點。挖掘許可查得到「有沒有挖」,查不到「車道可不可以這樣封」 |

---

## 第六輪:記錄者逐項復驗清冊後新開的(2026-09-22)

逐項證據與指令在 `docs/evidence-index.md`,編號 `EV-NN`。
下面每一條都是記錄者自己跑過或自己看過才開的,沒有一條是轉述清冊。

| # | 項目 | 證據 | 狀態 |
|---|---|---|---|
| **G30** | **§171「劃設時,外圍應以單實線界定」在 `docs/` 裡查無。** 借 `tests/test_basis_is_sourced.py` 的正規化去比,最長命中前綴只有「劃設」兩字 | EV-14 | TODO — **這是 E36 的同一種形狀**:法規名下的自造條文內容。第三點的「重大修正」目前整個靠這一句。驗收:要嘛把法規原文放進 `docs/` 並讓正規化比對全命中,要嘛把那句話從清冊與任何敘事裡拿掉 |
| **G31** | **§167 不是 0/42,是 1/42(F15),而且那一筆已證為偽陽性;同時 F07 裡另有一組兩條並排的白線沒被判讀過** | EV-25 / EV-26 / EV-27 | TODO — 清冊據 0/42 推論「現場可能根本沒有 §167」,前提不成立。另外 2025 街景那條槽化線外緣線與 F07 那一組不是同一條,「並排比對」比的是兩個不同物件。驗收:對 F07 那一組給出判讀(§167 單邊/雙邊,或槽化線邊線),並附幀號與座標 |
| **G32** | **§169 的引文與 repo 持有的版本不符。** 清冊寫「以劃設於路側或緣石正面及頂面」;`docs/evidence.md` L2 持有的是「以劃設於**道路緣石**正面**或**頂面**為原則**,無緣石之道路得標繪於路面上,距路面邊緣以三十公分為度」 | EV-15 | TODO — 多了「路側」、「或」改「及」、刪掉「為原則」與無緣石例外。驗收:改回逐字,或標為本程式改寫 |
| **G33** | **`430 公尺` 在 repo 內沒有出處。** 它是 `scripts/control_group.py:88` 的字面值,不是從 `data/ntpc/bridges.csv` 推出來的。用 repo 自己的兩個座標重算,site 點到橋頭是 **459.5 m** | EV-22 | TODO — G19 只說「此」沒有定義;現在連數值本身都對不上。驗收:由某個腳本從座標算出並登錄,或把 430 與依賴它的「31 秒」一起從敘事撤掉 |
| **G34** | **現場漆的速限是 30,不是 50。** F07 原解析度 `[1150:1600, 2150:3000]` 有兩處「30」。而正式跑 `results/assess_2026-09-22.json` 用的是 `--posted-kmh 50` | EV-33 / EV-34 | TODO — 清冊寫「施工期速限只有目擊證詞」不成立。用檔案內的 `taper_deg_bound` 對 `required_rate = 155/V²` 重算:V=30 門檻 9.77°,五張的最寬鬆讀數 9.86 / 4.15 / 4.04 / 7.61 / 8.11 → **`TAPER_TOO_STEEP` 在 30 下是 1/42,只有 F05**。驗收:正式跑改用 30,或在報告裡同時報兩個速限並說明哪一個有影像證據 |
| **G35** | **`results/chevron_angle.json` 沒有 `withdrawn` 標記**,清冊卻把它當成已撤回。三個登錄項(`chevron_to_boundary_deg` / `chevron_to_road_deg` / `chevron_method_spread_deg`)今天仍通過 `check_figures.py` | EV-20 | TODO — 兩者只能有一個對。驗收:要嘛在該檔寫 `withdrawn` 並移除三個登錄項與所有引用,要嘛把清冊那句「已 withdrawn」改掉 |
| **G36** | **登錄表有 9 項指向一個沒進 git 的檔案。** `results/assess_2026-09-22.json` 在 `git status` 裡是 `??`;而且它是在 `68708d0` 且 `src/marking/situation.py` 未提交的狀態下產生的,該模組的 sha256 已由 `c349282eea22d5eb` 變成 `619ee4538d5f6823` | EV-36 | TODO — 乾淨 clone 上 `check_figures.py` 會 9 項全炸。這是 M12 的新實例。驗收:把該 JSON 提交,並在檔內 `tree_state` 記錄與當時 HEAD 一致,或重跑後再提交 |
| **G37** | **`surface_types_stable()` 的穩定性旗標跨 process 不可重現。** 正式檔記 F30 `repeats [3,3,3,3,2]`、`stable False`;記錄者用同一張圖、同一個 `road_region` 遮罩(roi_frac 0.590740 對檔內 0.5907),在**兩個各自獨立的 process** 裡跑,其中一個連跑兩次,**四次全部得到 `(3, True)`**;同批的對照 F01 `(4, False)`、F38 `(4, True)` 四次皆與正式檔相同,所以不是整批偏移 | EV-12 | TODO — 回報值 3 兩邊一致,**不一致的是那個旗標**。正式檔是 4 workers 平行跑的,記錄者是序列跑的,差別最可能在 `cv2.kmeans` 的內部執行緒。所以登錄項 `assess_surface_types_unstable_n` 釘的那 15 張名單是**某一次平行執行的產物,不是方法的性質**。G23 驗收條件第 1 項量的是「同一 process 內兩次」,量不到這一種。驗收:在同樣的 worker 數下重跑並逐張比對名單,或把那個旗標的可重現性條件寫進 convention |
| **G38** | **來源 CSV 不在 repo。** `excavation_source_sha256` 釘的那份檔案只存在於暫存區,`data/` 又在 `.gitignore` 裡 | EV-05 | TODO — 摘要檔在 git 裡,但摘要要回溯就得有那份 CSV,而端點是即時的、明天抓到的不會是同一份。驗收:把該 CSV(或它的 gzip)納入 repo 的證據目錄,或在 `docs/evidence-index.md` 明寫這一項永遠只能靠摘要 |

**G26 的範圍要先改。** 清冊說「可騎乘的那一段就是中間那條有坑的帶」;
記錄者打開 F37 全幅與 F38/F39 的 `[2100:3400, 700:3000]` 看過:
槽化線外緣線到混凝土蓋板之間有**兩條帶** —— 較平整的灰瀝青 + 剷除帶 ——
**兩條都在可騎乘範圍內**,F37 裡的機車就騎在較平整那一側。
量「剩下多少寬度」要量這兩條的總和,不是只量有坑的那一條(EV-18)。

**一項不必修的更正。** 清冊第一點寫該許可「日間 09-21 時」。
那是 114-05-06 第一版的時段,已被取代;涵蓋拍照日的是
**第 7 次變更,115年09月08日起115年09月30日止,日間 09 時至 16 時**。
照片 15:56 開始、16:01 結束,**跨過那個時段的結尾**。
結論方向不變,但引用時要用 09–16(EV-03)。

| **G39** | `test_basis_is_sourced.py` 只檢查 `src/` 的 `basis` 字串,不檢查 `docs/` 裡以「§」宣稱的引文 | E49 | TODO — E49 那句自造引文寫在文件裡,所以檢查抓不到。驗收:把檢查擴到 docs/ 的引文區塊,並用 E49 那句做突變驗證 |

| **G40** | `check_stage.sh` 不檢查手機號碼等個資樣式,只檢查金鑰樣式 | E50 | TODO — 這次是人看欄位名才擋下來的。驗收:加上台灣手機(09xxxxxxxx)、市話、身分證字號的樣式檢查,並用那份原始 CSV 做突變驗證 |


---

## 圖表登錄:記錄者這一輪釘了什麼、哪些釘不住(2026-09-22)

`/opt/anaconda3/bin/python3 scripts/check_figures.py` → **49 項全過**。

### 釘住了(新增 17 項)

| 來源 | 項目 |
|---|---|
| `results/control_group.json#/sight_line/*` | `bridge_structure_id`、`bridge_near_end_m`、`bridge_length_m`(G19) |
| `results/assess_2026-09-22.json#/totals/*` | `assess_population` 42、`assess_findings_total` 74、`assess_photographs_with_a_finding` 39、`assess_distinct_finding_sets` 11、`assess_edge_not_carriageway_n` 25、`assess_carriageway_occupied_n` 9、`assess_surface_in_pieces_n` 34、`assess_no_lane_change_n` 1、`assess_taper_too_steep_n_at_50` 5、`assess_roi_frac_min` 0.555、`assess_roi_frac_max` 0.6001、`field_capture_span_s` 304、`field_fov_deg_wide` 56.812、`field_fov_deg_narrow` 31.516 |

`assess_*` 那一組的 `convention` 都寫明**這份跑批是用模組雜湊釘住的,不是用 commit**
(`tree_state.src_module_sha256_16`)。理由:這一輪有三個代理同時在 commit,
HEAD 在單一次跑批途中就動了兩次。雜湊變了就要重跑。

### 釘不住,逐項說明為什麼

| 數字 | 為什麼不登錄 |
|---|---|
| `_surface_types` 的「不穩定張數」(本輪 13/42,上一輪 15/42) | **它本身是隨機變數**。登錄它等於保證 `check_figures` 下次一定紅。證據改放 E43/E46,不放登錄表 |
| 跨種子散布(seed 0 給 34/42;seeds 0–4 要全部一致則給 20/42) | **沒有腳本產出它**。`surface_types_stable` 的 docstring 自己承諾「measured once offline and recorded」,**那個檔不存在** → G25(b) |
| ~~`docs/four-scenarios.md` 的 `TAPER_TOO_STEEP` 1/42、漸變段三態 20/21/1~~ | **已補齊**。記錄者另跑 `results/assess_2026-09-22_kmh30.json`(`--posted-kmh 30`,src 乾淨,`situation.py` 雜湊 `619ee453` = HEAD),六項已登錄。見下方「獨立重跑對帳」 |
| `src/marking/situation.py:479` 的「**31 秒**」 | 沒有腳本產出。它是 `430/(50/3.6)` 的心算,而 50 是**速限不是車速**(E31)。**在敘事裡是未登錄的數字** → G19 剩餘部分,併入 G20 |
| `results/control_group.json` 的 `taper_m` 14.9、`erased_share`、`time_available_s`、整個 `day` 陣列 | **刻意不登錄**。14.9 由已撤回的 0.202 抄成常數而來,而該檔自己沒有 `withdrawn` 標記,`check_figures` 第三條規則看不見它。登錄=用檢查替一個已撤回的量測背書(E35 → G22) |

**一個仍未關的迴圈**:`results/figure_registry.json` 在 2026-09-22 被覆寫過一次,
記錄者先前加的 12 項 `assess_*` 整組消失(3 項 `bridge_*` 倖存),
是另一個代理以較舊的版本整檔寫回造成的。已重新加回。
**這個檔沒有任何機制擋住「整檔覆寫」** —— `check_figures` 只檢查「在裡面的項目對不對」,
不檢查「該在裡面的項目還在不在」。**沒有一條規則會發現一個登錄項被刪掉。**


---

## 獨立重跑對帳:記錄者對 `docs/four-scenarios.md` 的頭條表(守則 8)

**沒有複述,全部自己跑。** 主代理在 `2d641ed` 用 `posted_kmh 30` 跑;
記錄者在 HEAD(`situation.py` 雜湊 `619ee453`)用同樣的 30 重跑,
輸出落檔 `results/assess_2026-09-22_kmh30.json`。

| 項目 | 主代理(`2d641ed`,posted 30) | 記錄者重跑(HEAD,posted 30) | |
|---|---|---|---|
| `EDGE_NOT_CARRIAGEWAY` | 25/42 | **25/42** | 一致 |
| `CARRIAGEWAY_OCCUPIED` | 9/42 | **9/42** | 一致 |
| `NO_LANE_CHANGE` | 偵測 1/42 | **偵測 1/42**(F15) | 一致 |
| `TAPER_TOO_STEEP` | 1/42 | **1/42** | 一致 |
| 漸變段三態 | 20 / 21 / 1 | **20 / 21 / 1** | 一致 |
| `roi_frac` 範圍 | 0.5550–0.6001 | **0.5550–0.6001** | 一致 |
| `SURFACE_IN_PIECES` | 33/42(自己標「不可重現」) | **34/42**(定種子後,seed 0) | **不同,原因已知:E43/ER01** |

**地點一逐項也對得上**(F01–F08,記錄者自己那份 posted 50 的跑批):
圍籬 7/8(F04 偵測到但 `width_frac` 未過門檻)、紅線 3/8(F01/F03/F06)、
`SURFACE_IN_PIECES` 8/8、`TAPER_TOO_STEEP` 1/8(F05)。

**F05 漸變段那五個數字,逐一重跑確認**
(`scripts/assess_field.py --photo F05 --posted-kmh 30`):

```
state = STEEPER_THAN_REFERENCE
readings = 6                      主代理寫「6 個讀數」        一致
taper_deg_bound = 9.86            主代理寫「最寬容的 9.86°」   一致
required_deg = 9.77               主代理寫「對參考 9.77°」     一致
times_required_at_least = 1.01    主代理寫「1.01 倍」          一致
taper_deg_spread = 6.74           主代理寫「散布 6.74°」       一致
equivalent_kmh_at_most = 29.9     主代理寫「至多 29.9 km/h」   一致
```

**唯一的不一致是 33 對 34,而兩邊都已經知道原因。**
主代理那份跑在定種子之前(當時 `SURFACE_IN_PIECES` 是一次抽獎,他自己也這樣標);
HEAD 定了種子之後,seed 0 穩定給 34。
記錄者兩次未定種子的全母體跑批也都是 34。
**33 不是錯的,是同一顆硬幣的另一面 —— 這正是 E43 在講的事。**

| **G41** | F07 的真雙白線仍抓不到:真線區塊併後只有一條 226 px 線段,門檻 614 | E52 | TODO — **不是解析度**:橫切量到亮段寬 23–35 px,而非像素預算的 4 px。缺口在漆遮罩的連續性。驗收:量出那條線上 `markings()` 的 response 剖面,找出斷在哪裡。**剖面已量,見下方〈G41 獨立復驗〉:根因是響應峰值落在兩線之間的暗間隔,不在漆上;修 `extract.dark_light_dark`,不是修 `situation.py`** |

---

## G41 獨立復驗（記錄+驗證者，2026-09-22）

角色:記錄者/驗證者。不改 `src/`。重跑腳本 `isolation/scripts/g41_verify.py`,
影像 `isolation/out/g41/`(f07_mask_kernels.jpg / f07_bars_small.jpg / zoom_bar2.jpg / zoom_bar3.jpg)。輸入 `evidence/field-2026-09-20/IMG_20260920_155735.jpg`,
sha256 `f7ffca88480b93eb580874ba5816dfe83d3e881a3413d521ba1542a56dcf1d28`,
shape 4096x3072,`/opt/anaconda3/bin/python3` cv2 5.0.0 / numpy 2.4.4。
區塊定義 x 1400–2650, y 1450–2100(下稱「該區塊」)。

### 四項既定事實:兩項成立、一項要修正、一項不成立

**claim 1 —— 修正。該區塊裡不是「一條 226 px」,是零條。**

```
$ /opt/anaconda3/bin/python3 isolation/scripts/g41_verify.py claim1
_segments(F07): 58 raw segments, roi_frac 0.5766
_merge_collinear: 37 segments
block (1400, 2650, 1450, 2100): 0 merged segments, lengths []
length threshold in _double_white: h*0.15 = 4096*0.15 = 614.4 px
whole frame: longest merged 639.9 px, 1 clear h*0.15
```

沒有任何線段的端點或中點落在該區塊內。最接近的一條是
`[2832.0, 2116.0, 2993.0, 1955.0]` 長 **227.7 px**,在區塊右下角**外面**
(x 上界 2650、y 上界 2100 都越界)。226 這個數字對得上,位置對不上。
結論方向不變(Hough 抓不到),但「該區塊有一條 226 px 線段」這句話不成立。

**claim 2 —— 成立,但把「不是解析度問題」講得比證據更強了。**

```
$ ... claim2
  y= 1550  runs [23]
  y= 1600  runs [24]
  y= 1650  runs [26, 26]
  y= 1700  runs [27, 29, 28, 39, 37, 35]
  y= 1800  runs [27, 30, 32, 36, 39]
  bright-run widths: n=57 min=5 max=75 median=19
components in block with area>=400: 40
  area   6007  mean L*  207.5  bbox 2168,1450 309x182
  area   3272  mean L*  175.0  bbox 1818,1632 339x199
  area   3047  mean L*  107.0  bbox 1512,1450 46x153
pixel budget: 19 m -> 10.8 px, 40 m -> 5.1 px, 65 m -> 3.2 px(0.10 m 線寬)
```

23–35 px 那段對(y 1550–1850 的核心帶),但全區塊分布是 5–75、中位數 19。
「元件 L* > 200」只有最大的兩個成立(207.5 / 207.4),第二、四大是 175.0 / 162.0。
像素預算我自己算是 19 m 給 10.8 px、65 m 給 3.2 px,「約 4 px」對應的是遠端。
**順帶一個沒人提的矛盾**:量到 23–35 px 的亮段,若真在 19–65 m,
對應地面寬 0.21–1.1 m,不是 10 cm 線。要嘛物距比 19 m 近得多,要嘛那不是單條 10 cm 線。
這一點會直接影響 `S167_GAP_TO_WIDTH` 這種比例判準的前提,建議另開一項。

**claim 3 —— 不成立。**

```
$ ... claim3
cached-response reconstruction == markings(min_response=4.0): True
  min_response= 8.0  paint coverage  20.7%  in block   0  >=h*0.15 in block 0  longest    0.0 px
  min_response= 6.5  paint coverage  32.9%  in block   1  >=h*0.15 in block 0  longest  166.7 px
  min_response= 5.0  paint coverage  52.1%  in block  17  >=h*0.15 in block 3  longest  801.2 px
  min_response= 4.0  paint coverage  67.2%  in block  23  >=h*0.15 in block 1  longest  702.2 px
```

覆蓋率 20.7% → 67.2% 完全對得上。但「四個門檻的長線段都是 0」是錯的:
**5.0 給 3 條、4.0 給 1 條**過 614 px。只有 8.0 和 6.5 是 0。
所以「不是門檻問題」這句話下得太早 —— 它**是**門檻問題的一部分,
只是要把覆蓋率推到 52% 才換得到,那時候遮罩已經不能用了。

**claim 4 —— 修正。該區塊裡只有一個物件,不是兩個。**

```
$ ... claim4   （contours + minAreaRect,裁到該區塊）
  close no close: 0 bar-shaped objects
  close 3x3     : 0 bar-shaped objects
  close 5x5     : 0 bar-shaped objects
  close 9x9     : 1 bar-shaped objects
       433.8 x  60.5  ar  7.17  ang  148.9  centre ( 1972.7, 1743.8)
```

434x60.5(比 7.17)確實存在,而且**只在 9x9 閉運算下存在**;不做閉運算是 0 個。
另一個 415x37.9(比 10.95)不在該區塊裡 —— 它在全幀 `_paint_bars` 才出現,
中心 (1411.4, 1761.7),而且**它不是線**(見下)。

### 關鍵懷疑:成立,而且比懷疑的更嚴重

`isolation/out/g41/f07_mask_kernels.jpg`(原解析度疊圖,已親眼看過)。
垂直於線軸的剖面,u = 帶正負號的法向偏移:

```
$ ... （perpendicular profile, raw L* vs markings(8.0) mask）
u = signed perpendicular offset (px). paint = L*>=190, mask = markings(8.0)
  t= -180  paint runs [(-20, -7), (10, 22)]   mask runs [(-22,-14), (-8,-5), (-1, 4), (7,15)]
  t= -120  paint runs [(-21, -7), (11, 24)]   mask runs [(-12,-12), (-1, 5), (9,15), (22,22)]
  t=  -60  paint runs [(-21, -7), (11, 24)]   mask runs [(-7,-7), (-1, 5), (10,13)]
  t=    0  paint runs [(-22, -7), (13, 26)]   mask runs [(-1, 5)]
  t=   60  paint runs [(-23, -7), (14, 27)]   mask runs [(-31,-31), (0, 5), (16,16)]
  t=  120  paint runs [(-23, -7), (13, 28)]   mask runs [(0, 5), (19,19), (30,30)]
  t=  180  paint runs [(-23, -6), (14, 29)]   mask runs [(-2,-1), (13,13), (20,26), (29,29)]
```

**地面真值(從原照片量的,不是從遮罩)**:兩條線各寬 **14–18 px**,
中間暗間隔 **17–19 px**。gap ÷ width ≈ **1.13**,而 §167 規定的是 1.0 ——
**若能把兩條分開,比例判準本來會過**(容許 1.0±0.6)。

**遮罩做的事正好相反。** 七個取樣站裡,`markings(min_response=8.0)` 唯一
每站都出現的連續 run 是 **u ∈ [-1, +5]**,也就是**暗間隔的正中央**;
兩條真線身上只有零碎片段。response 剖面證實:

```
  t=    0  paint: max r   7.89 mean r   7.16 (n=30, L* 211-241) | gap: max r  11.30
  t=  -90  paint: max r   8.53 mean r   7.68               | gap: max r  10.67
  paint 取樣 n=12088: r>=8.0 只有 22.5%,r>=6.5 有 86.7%,r>=5.0 有 98.5%
  median r on paint 7.40, p90 8.44, max 27.08
```

**漆上的 response 中位數 7.40,低於門檻 8.0;暗間隔的 response 最高到 11.4。**
`dark_light_dark` 把「兩條線 + 中間間隔」當成一根寬 bar,峰值落在間隔上。
這是 G41 的真正上游原因,比「閉運算併線」更早一層。

核大小掃描(該區塊,area>=400):

```
$ ... kernel
  close none  : 20 components, 16 contours; top rects [(387,29.3),(272,14.3),(191,28.7),(171,12.7)]  覆蓋  6.6%
  close 3x3   : 20 components, 16 contours; top rects [(387,29.3),(272,14.3),(191,28.7),(171,12.7)]  覆蓋  6.6%
  close 5x5   : 26 components, 23 contours; top rects [(395,47.3),(315,53.1),(294,46.6),(240,48.3)]  覆蓋  8.8%
  close 9x9   : 23 components, 23 contours; top rects [(434,60.5),(432,149.0),(392,264.0),(359,60.4)] 覆蓋 14.3%
  close 15x15 : 16 components, 14 contours; top rects [(881,435.0),(443,64.6),(365,109.6)]            覆蓋 25.4%
  close 25x25 : 9 components,  9 contours; top rects [(977,461.0),(529,90.3),(365,110.9)]             覆蓋 39.9%
```

最寬的 bar 寬度 **29.3 → 47.3 → 60.5 → 435**,隨核大小單調上升。
把 9x9 那一個 434x60.5 物件的足跡拿回去對未閉運算的遮罩:

```
pre-close components inside that one 9x9 object: 35   （area>=200 的有 5 個）
   area  3028 bbox 1818,1638 337x193
   area   465 bbox 1772,1812  60x 21
   area   349 bbox 2104,1663  48x 11
   ...
```

**答案:會,而且不只併兩條線 —— 它把 35 個碎片焊成一根。**
60.5 px 正是兩條線加間隔的整個包絡(量到 46–51 px)再加遮罩外溢。
所以在真線的位置上,`_paint_bars` 永遠只交得出**一個**物件,
`_double_line_from_bars` 沒有第二個可以配。
把核降到 3x3 或不做也救不回來:那時真線位置一個 bar 都不剩
(最長 387 px < `min_len_frac=0.10` 的 409.6 px);
就算把 `min_len_frac` 放寬到 0.06,真線位置仍只有 **1** 個 bar(386.9x29.3),
因為第二條線在遮罩裡根本沒被標出來。

### `_double_line_from_bars` 回 None 的確切原因

```
$ ... pair
_paint_bars(F07, roi) -> 4 bars over the WHOLE frame
  bar[0] centre (  765.2, 2060.1) len 1037.7 width 125.9 ar  8.24 ang 162.8
  bar[1] centre (  772.7, 1872.1) len  554.8 width  95.4 ar  5.81 ang 154.9
  bar[2] centre ( 1411.4, 1761.7) len  414.7 width  37.9 ar 10.95 ang 158.2
  bar[3] centre ( 1972.7, 1743.8) len  433.8 width  60.5 ar  7.17 ang 148.9
_double_line_from_bars(F07, roi) -> None

  pair(0,1) angle_d  7.87 wratio 1.32 gap  172.6 g/w 1.559 contrast  30.0 -> REJECT: angle 7.87 > 6
  pair(0,2) angle_d  4.56 wratio 3.32 gap   65.4 g/w 0.798 contrast  55.5 -> REJECT: width ratio 3.32 > 2.0
  pair(0,3) angle_d 13.85 wratio 2.08 gap  205.7 g/w 2.206 contrast -14.0 -> REJECT: angle; width ratio; g/w; contrast
  pair(1,2) angle_d  3.31 wratio 2.52 gap  152.9 g/w 2.293 contrast  21.5 -> REJECT: width ratio 2.52 > 2.0
  pair(1,3) angle_d  5.98 wratio 1.58 gap  452.0 g/w 5.796 contrast  28.0 -> REJECT: g/w 5.796 outside 1.0+-0.6
  pair(2,3) angle_d  9.29 wratio 1.60 gap  234.0 g/w 4.755 contrast  27.5 -> REJECT: angle 9.29 > 6; g/w 4.755
```

**六對全被拒,沒有哪一條判準是主因 —— 因為根本沒有一對是那條雙白線。**
真線整條在 **bar[3] 一個物件裡面**。
主代理以為的「那一對」是 pair(2,3),它被 **角度 9.29° > 6°** 和
**間距比 4.755 遠離 1.0±0.6** 兩項同時拒絕;暗度(contrast 27.5 ≥ 18)和
顏色(b* 131.0/131.0 同側)都**通過**,不是它們擋的。

而 pair(2,3) 就算過了也是偽陽性:**bar[2](414.7x37.9)不是線,是路面文字的筆畫。**
畫框在原解析度看過 —— `isolation/out/g41/zoom_bar2.jpg` 是「東」字的橫豎筆畫,
`isolation/out/g41/f07_bars_small.jpg` 裡 bar[0]/bar[1] 同樣壓在「林」字與左側標線上。
四個 bar 沒有一個是「一條線的一員」。

### 結論鏈

1. `dark_light_dark` 在這條雙白線上的連續響應脊落在 **17 px 的暗間隔**(u≈+1..+5),
   不在兩條 15–16 px 的白漆上;漆上 response 中位數 7.40 < 門檻 8.0。
2. 所以遮罩在真線處是「中間一條細帶 + 兩側碎片」→ Canny+Hough 在該區塊得 **0** 條線段。
3. `_paint_bars` 的 9x9 閉運算把那 35 個碎片(含兩條線與中間帶)焊成 **1** 個 434x60.5 物件。
4. `_double_line_from_bars` 因此在真線處永遠只有一個物件,配不成對;
   它實際嘗試的 pair(2,3) 把真線配給了一個文字筆畫,被角度與間距比拒絕。

**建議的驗收點(未實作,留給主代理拍板)**:修 3 沒有用,要修 1。
判準是「`markings()` 的 response 峰值要落在漆上、不落在兩線之間的暗帶」,
量法就是上面那份 u 剖面 —— mask 落在漆上 vs 落在暗間隔上的比率。
沿線軸 401 站 x 法向 91 px 逐點量(同一份 `markings(8.0)` 遮罩):

```
paint pixels 12088, of which in mask 2816 = 23.3%
gap   pixels  6382, of which in mask 2565 = 40.2%
```

**遮罩蓋住暗間隔的比例(40.2%)幾乎是蓋住白漆的兩倍(23.3%)。**
修好的判準:這兩個數字要倒過來。
(先前這裡寫「重疊率約 0%」,是我自己沒量就寫的,已量並更正。)
在 1 修好之前,調核大小、調 `min_len_frac`、調 `tol` 都只是在挑焊點。

**狀態:TODO —— 根因已定位到 `extract.dark_light_dark`,不在 `situation.py`。**

| **G42** | 漆的響應與柏油雜訊的響應重疊,單一全域 `min_response` 分不開 | E54 | TODO — 線的 response 中位 7.4–7.7,門檻 8.0;降到 5.0 抓得到但全幀一半被標成漆。方向:相對門檻(對該幀分布取分位)或讓 `dark_light_dark` 的尺度適應線寬。**在量出 42 張上的偽陽性代價之前不得採用** |
