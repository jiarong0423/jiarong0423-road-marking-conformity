# 這個專案在主張什麼

**OpenCV 能不能把道路標線的法規，變成一個跑得動的檢查——在標線造成
駕駛困擾之前，就指出幾何上不合理的設計。**

不是「這條路違規」。那是陳情。這是工具。

## 問題的形狀

台灣的標線規範寫得很具體：斜紋 45 度、線寬 20 公分、間隔 30 公分、
車道虛線 4 公尺配 6 公尺、漸變段 `L = W·V²/155`。全部是數字。

**但沒有人在查。** 查一條路要派人拿皮尺，所以實務上只有出事之後才回頭看。

而標線不合理的代價落在用路人身上：一段只夠 28 km/h 的漸變段畫在
速限 50 的路上，駕駛不會知道，直到他來不及併道。

## 為什麼是 OpenCV 而不是深度學習

**因為法規是幾何，不是分類。**

「這條線是不是 45 度」不需要學習，需要量測。需要的是邊緣、直線、
透視還原、週期偵測——這些是古典電腦視覺做了三十年的事，而且：

- **可稽核**。Hough 抓到的每一條線都能畫出來給人看。神經網路說「不合規」
  沒有辦法反駁。
- **不需要標註資料**。法規就是標準答案，不用人去標。
- **跨地區可遷移**。換一個國家就換一組數字，不用重訓。

這個專案裡 OpenCV 實際做的事：

| 步驟 | OpenCV |
|---|---|
| 從路面分出標線 | Otsu 門檻（`cv2.threshold`），讓每張影像自己決定 |
| 找線段 | `Canny` + `HoughLinesP` |
| 找地平線與消失點 | 線段交點最小平方解 |
| 還原到地面 | 針孔模型 + `warpPerspective` |
| 驗證幾何正確 | 沿標線的亮度自相關，週期必須是整數倍 |
| 形狀（箭頭、槽化區） | `findContours` + 凸包缺陷 |
| 去除車輛與行人 | `cv2.dnn` 分割 |

## 三個設計決定

**一、量比率不量長度。** 橫向偏移 ÷ 縱向距離是無因次的，相機高度會消掉。
這讓一張手持照片就能判漸變段，不用量測桿也不用已知尺寸物。

法規要求的率也剛好無因次：`rate = W/L = 155/V²`，與車道寬無關。

**二、用法規自己的尺寸當比例尺。** 需要絕對長度時，車道虛線是 4 公尺、
斜紋週期是 50 公分——**被檢查的對象和校準的基準必須是不同的東西**，
否則是循環論證。

**三、判不下去就拒答。** 這是整個專案的核心，也是它跟「AI 說這裡違規」
的差別。

## 拒答為什麼是重點

量測有誤差。法規門檻是一條線。當量測值落在門檻附近、而誤差跨過那條線時，
**任何答案都是錯的**——不是不夠準，是問題本身答不了。

JCGM 106《不確定度下的符合性評估》就是為這件事寫的標準。三態輸出：

```
符合      量測值超出門檻，超出的幅度大於方法自身的誤差
需人工    落在 guard band 內，人來判
影像不足  這張照片撐不起這個量測
```

現有做法報一個點估計。在人行道寬度那個相鄰領域，最好的方法報 MAE
0.252 公尺，而三分之一的真實人行道離法規門檻不到半公尺——**那些案例
它全部都會給答案，而且其中一部分是錯的。**

## 目前的證據

一個真實案例，116 縣道樹林段，捷運土城樹林線 CQ890 標施工路段：

| 量到的 | 值 | 驗證 |
|---|---|---|
| 漸變率 | 11.4°（相當於設計速率 27.8 km/h） | 兩種視角差 1.4° |
| 槽化帶寬 | 1.60 m | 斜紋週期自相關峰為整數倍 |
| 槽化線角度 | 對邊線 46.4°、對行車 57.5° | 三種焦距差 1.97° |

法規要求：原速限 50 → 3.5°，施工速限 30 → 9.8°。實測 11.4°。

〔已撤銷 2026-09-21，見 `docs/reproducibility-2026-09-21.md`：同一張照片換編碼即移動 11.5–17.3 度〕

**而該路段 A2 事故從施工前每月 1.00 件升到施工期間 2.62 件，
同期全國持平（1.04 倍），Poisson p = 0.00016。**

事故關聯不能歸因到單一標線，但它證明這類檢查值得做。

## 還不是什麼

- **一個路口不是一個工具。** 要成立必須在多個地點跑得動。
- **沒有大規模驗證。** 目前每個數字都是單點量測加重複性檢查。
- **只涵蓋三種標線**（槽化線、車道線、漸變段），法規還有幾十種。

## 下一步

1. 跑 20–30 個路口，看方法的失敗率與拒答率
2. 把三條法規寫成可宣告的規則檔，而不是寫死在程式裡
3. 一張照片進、一份判定出的完整流程

---

# 四個時期的比較，以及它失敗在哪

2026-09 有一次真實的標線重新設計（議員會勘後）。同一條路四個時間點，
用同一條管線量——工具能不能看出重新設計改了什麼，本身就是主張的檢驗。

跑出來的結果：

| 時期 | road | edge | stripe | 漸變角 | ≈設計速率 |
|---|---|---|---|---|---|
| 2022-11 開工當月 | — | — | — | — | — |
| 2024-09 圍籬進場 | 24.0° | — | 80.8° | — | — |
| **2025-06 槽化線** | 4.6° | 15.6° | 61.8° | **11.0°** | **28.2 km/h** |
| 2026-09 調整後 | 15.1° | 40.0° | — | 24.9° | 18.3 km/h |

**只有 2025-06 那列可信。** 它跟先前用兩張不同視角量到的 11.4° / 27.8 km/h
一致（差 0.4°），那是重複性。

## 其他三列為什麼不可信

**特徵辨識失敗，不是量測失敗。**

幾何本身沒問題——焦距、俯角、地面投影都通過驗證。失敗的是**「哪一群線
是漸變段邊界、哪一群是斜紋」這個判斷**。

目前的做法是按地面方位角落在哪個區間來分。那預設**相機大致沿著路的方向**。
街景是我自己設 heading 128 沿路抓的，所以成立；使用者站在人行道上斜著拍，
路在畫面裡是斜的，區間就對不上了。

2026-09 那列的 24.9° 很可能是把斜紋當成了邊界。

### 已經修掉一半

第一版更糟：我用「絕對方位角小於 10 度就是道路方向」，那等於假設相機朝著
路。改成從**消失點**取道路方向之後，至少道路方向是量出來的而不是假設的
——消失點本來就是路面平行線定義的。

但「邊界 vs 斜紋」還是靠相對角度區間分，那一步還沒有真的解法。

## 不調參數

把區間調到 2026-09 也給出好看的數字是辦得到的。不做，理由是：
**四個時期只有一個有已知答案可以對照**，用其他三個去調參數就是拿沒有
答案的資料來校準，調完之後那四個數字沒有一個能信。

## 這反而是主張的一部分

一個會在視角改變時安靜給出錯誤答案的工具，比沒有工具更糟。

現在這條管線的正確行為應該是：**辨識不出三個特徵群時拒答**，而不是
把最接近的那群當答案。那跟 guard band 是同一個原則——
**判不下去就說判不下去**。

目前的程式沒有做到，它照樣輸出了 18.3 km/h。**那是一個 bug，
而且是這個專案最該修的 bug。**

## 需要的是什麼

不是更好的區間，是**不靠角度的特徵辨識**：

- 斜紋是**週期性**的（自相關有整數倍峰），邊界不是——那是可判別的性質
- 邊界是**兩條平行且相距 15 cm**（§171 周圍邊線），斜紋之間相距 30 cm
- 邊界**連續**，斜紋**斷續**

這三個都不看角度。角度是要量的東西，不該同時拿來當辨識依據——
那是循環的，跟先前「用被檢查的對象校準自己」同一類錯誤。

## The claim this project is actually making

Taiwan re-marks its roads often, and the marking is set out by maintenance
crews rather than designed to a reaction-time budget. When the geometry is
wrong the driver does not get a warning; the driver gets less room than they
need and finds out at the point of no return. The question OpenCV is being
asked here is narrow and checkable: **can the angle, extent and distance of a
marking be measured from ordinary imagery well enough to say whether a driver
can react to it?**

At 116 縣道 (樹林中正路) the answer so far, in order of how well it is
established:

**Settled.** The taper rate is 0.202, from two independent Street View
captures at different fov and pitch (10.7° and 12.1°). On a 3.0 m lane that
is a taper 14.9 m long. A driver covers it in 1.07 s at 50 km/h and 1.78 s at
30 - both shorter than the 2.5 s perception-reaction time in the design
standards. Reacting to the narrowing and then slowing 50 → 30 needs 52.9 m
from first sight of the sign; there are 14.9 m. Against the taper formula
L = W·V²/155 the taper is 1.2x too short for the posted 30 and 3.3x too short
for the 50 the road carried before the works. (`results/reaction.json`)

**Visible, and not yet measurable.** Part of the chevron has been ground off
and the asphalt keeps the imprint: the same stripe angle, the same repeat,
running on past where the paint stops. Anyone can see it in F17. No detector
tried here can find it reliably, and two numbers produced along the way -
25% and 16% of the original band width - are withdrawn. Both came from a
test that a large fraction of plain carriageway also passes, so they were
measuring the threshold, not the marking.

The obstruction is specific. An erased stripe and the gap between two
painted stripes are locally the same object: a dark bar about a stripe wide,
at the stripe angle, lighter material either side. Nothing that looks only at
the bar can separate them. What separates them is what lies on the flanks -
paint means a gap, asphalt means an imprint - and that test does work: it
recovers every real gap in the painted band, which is a check with a known
answer. It still does not find the imprint, because the imprint's contrast
sits under the level at which the bar detector fires at all, and dropping
that level lets tyre marks in.

**Resolved, with the original edge supplied by hand.** The site owner drew
the chevron's former edge over F17. Registered onto the photograph by SIFT
homography, it closes the measurement without a detector: the still-painted
周圍邊線 on the far side, the edge where the paint now stops, and the drawn
edge are three parallel ground lines, so they meet at a vanishing point, and
a cross-ratio against that point converts image distances into ground
distances exactly - no focal length, no camera height, no pitch.

Each chevron stripe is a transversal cutting all three, so the frame gives
one independent measurement per stripe:

    erased 64% of the original chevron width
    median of 23 stripes, sd 11%, quartiles 60-66%

The same stripes read straight off the image, without the cross-ratio, give
59%; the five-point difference is what perspective was doing to every earlier
attempt.

The estimate that prompted this was about a half. The measurement says
**more** was taken out than that, not less.

One step had to come first and is the reason the earlier cross-ratio attempt
scattered from -4% to 85%. In the paint mask the stripes are fused to the
boundary line - one component holding 44% of all paint - so
connected-components returns fragments, and seven of those fragments were
being used as transversals. An opening with a 91 px line element along the
band isolates the boundary; removing it leaves 52 separate stripes, of which
23 cut all three lines cleanly.

What the number rests on: the drawn edge is an input, not a measurement. If
that line is the resurfacing boundary rather than the chevron's own former
edge, the 64% is measuring something else, and only the person who stood
there can say which.

**Established regardless of that number.** Every imprint runs *toward the
carriageway*. The chevron used to be wider on the traffic side and was
narrowed there, while the right-hand side was re-marked as a lane reduction.
Both changes move the point at which a driver must already have changed lane
*earlier*, into a taper that was measured above as too short at any speed the
road carries.

### Four ways of measuring the erasure that did not work

Kept because each one fails for a reason the next had to design around, and
because the third is not obvious.

1. Autocorrelating a high-pass residual along the band: every lag pinned to
   the search minimum. That is noise with a period, not a stripe period.
2. Thresholding the imprint as *brighter* than its surroundings: wrong sign.
   Ground-off asphalt is darker, not lighter.
3. Thresholding it as *darker*: an erased stripe and the gap between two
   painted stripes are both dark relative to a local mean dominated by white
   paint. Brightness cannot separate them at all.
4. A Gabor bank tuned to the stripe frequency: the period came back at the
   clamp value, so the FFT had not found the stripes, and the band grew to
   78% of the frame. 84.1% came out of it, which is an artefact and is
   recorded here only so it is not mistaken for a result later.

5. Walking out from each painted stripe along its own axis, calling the
   imprint over where the residual fell below -4. Roughly half of all
   non-paint pixels in the frame are below -4, at every depth, so the test
   was not selecting anything. The walks that stopped had run into paint or
   out of frame. This is where 25% and 16% came from.
6. A matched dark-bar filter at the stripe angle and width: fires hardest on
   the gaps, for the reason in 3.
7. The same filter, with the flanks used to separate gap from imprint. The
   gap class is correct - it reproduces every real gap, a check with a known
   answer - but the imprint class is tyre marks, because the imprint never
   clears the detector's threshold.

The pattern across all seven is one thing: the imprint is easy to see and
hard to threshold, and each time I reached for a stronger operator when what
was missing was a labelled example to set the level against.

## The taper after the re-marking: not measured, and why

The taper rate is the one figure here that needs no scale, so it should have
been the easy before-and-after. It is not, and the reason is worth recording.

The 0.202 on 2025-06 Street View is sound because the Static API is *told*
the field of view and the pitch; the request fixes them and the rectification
follows. A phone photograph gives neither. The focal length comes back from
EXIF (f35 24 mm, so 2840 px on a 5120 px diagonal, fov 56.8°), but the pitch
has to be recovered from the horizon, and on eight field frames the recovered
pitch ran from -8.0° to +19.6°. Twenty degrees of *upward* tilt in a
photograph of a road surface is not a pose, it is a failed estimate.

What came out the other side:

    relative bearing 5.00 to 24.00 degrees over eight frames
    taper rate 0.087 to 0.445
    equivalent design speed 18.7 to 42.1 km/h

A five-fold spread in the rate. The mean, 0.186 and 28.9 km/h, lands close to
the 2025-06 figure, and that closeness is meaningless - it is the average of
eight bad numbers, and quoting it would be the same error as the 84.1% and
the 25% before it. The frames also reproduce 24.0° / 18.7 km/h on F17, which
is within half a degree of the 24.9° that compare_epochs.py produced and that
was rejected in the same terms. The same failure, arrived at twice.

There is no Street View after the change. The metadata endpoint returns
2025-06 for every panorama within 40 m of the site, on all four field
coordinates, so the post-re-marking state exists only in the 2026-09
photographs.

Two device routes are closed: the phone writes no attitude data - no pitch,
roll or yaw in EXIF, and the vendor blob holds only HDR and zoom settings -
and GPS is off, every field NaN.

That leaves one pitch reference that is known to work at this site. The
erased-width measurement stalled for seven attempts and then closed in a
single pass once the site owner drew the chevron's former edge by hand. Two
lines along anything known to run parallel with the road - the kerb, a lane
line, the far boundary - would fix the horizon the same way, and the taper
after the change would follow from the method already written.
