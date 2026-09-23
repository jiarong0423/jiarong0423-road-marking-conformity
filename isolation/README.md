# 隔離區

2026-09-21。這裡的東西**不在交付路徑上**,而且是被主動搬出來的,不是忘了刪。

## 為什麼有這個目錄

這個專案的主軸是**一個場景**:116 縣道(樹林中正路)上,一個騎士在幾秒內
被三件事同時夾住。主軸寫在 repo 根目錄的 `README.md` 最上面。

從交付物往回倒著追,實際的路徑只有四層:

```
白話場景敘事  ← 只由 findings 組成,沒有 finding 就沒有那一句
      ↑
6 個檢查   taper / double_white / kerbside_red / works_hoarding / surface / lane_width
      ↑
2 個共用中間物   roi = carriageway(image)   segs = _segments(image)
      ↑
3 個輸入   影像 + 視角 + 速限
```

在這條路徑上的模組是 `situation` `extract` `sequential` `gate2` `vanishing`,
另外 `rectify` 供 Street View 的腳本用,`draw` 供製圖用。

這個目錄裡的四個模組,`aws/handler.py` → `situation.assess()` 一行都不會呼叫到。

## 裡面是什麼,各自為什麼在這裡

| 模組 | 為什麼隔離 |
|---|---|
| `pipeline.py` | 2026-09-21 寫的八階段量測管線。階段 2(地平線)三次擬合三次沒過自己的保留校驗;階段 3(比例尺)在 42 張上全是 NONE;階段 4 被缺平面與缺比例尺擋住兩次;階段 5 的條文述詞成立但 §171 沒有定位器。**整個檔案沒有被部署路徑引用過。** |
| `route.py` | 拒答路由,把信心從 0.27 調到 0.91 的那份工作。它會呼叫判斷模型,放進 `assess()` 會讓評估變成非決定性、依賴網路,直接牴觸本專案的可重現性主張。 |
| `identify.py` | 沒有任何檔案 import 它。 |
| `gate.py` | 舊的單問題閘門,已被 `gate2` + `situation` 取代。`situation.py` 裡出現的 `gate` 字樣全在註解裡。 |

腳本 `plane_holdout.py`、`stage5_predicate.py`、`route_refusal.py` 只服務上面這些,
一起搬進來。它們產出的 `results/*.json` 留在原位:那些是**負面結果的證據**,
是這個專案主張的一部分,不是垃圾。

## 這不是刪除

隔離區的東西是查得到、跑得起來、而且有紀錄的。`pipeline.py` 的階段 3、4 是
正確的分析,它們的正確結論就是「拒答」;`stage5_predicate.py` 的 duty 估計器
和它的保留式諧波校驗是可用的。哪天現場量了尺、或換了場景需要逐條文判定,
從這裡接回去,不必重寫。

搬出來只說明一件事:**它們不在「一個騎士在這個路口遇到什麼」這條線上。**
