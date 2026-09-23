> **Historical working note (content from 2026-09-20).** Numbers and status here may be superseded. The current account is [`technical-report.md`](technical-report.md); withdrawn figures are listed there.

# The tolerance, found at last

`docs/markings-regulation.md` listed this as the thing that would give an
accept/reject band an external basis instead of one derived from my own
scatter. It exists.

## 臺北市政府 第 02898 章 標線, TPE V4.0, 111/04/11, §3.3 許可差

> **3.3.1 標線長度**：每一縱向 3m 標線之許可差為±5cm。
> **3.3.2 標線寬度**：標線寬度之許可差為±6mm。
> **3.3.3 車道寬度**：車道寬度為從路面邊緣至標線中心，或兩標線之中心間距，
> 其許可差為±5cm。
> **3.3.4 標線之線形**：標線之橫向位置與契約圖說所示及工程司核可之位置，
> 其許可差為±5cm。

Full text kept at `docs/source-02898-tolerances.txt`. The chapter is 02898,
not the 02890 or 02891 guessed at earlier. The external search returned
nothing for this question; the document came from 臺北市政府's own download
endpoint after the 公共工程委員會 host failed to resolve.

## What it settles

**§3.3.4 is the clause that matters.** A marking's lateral position may
differ from the drawing by ±5 cm. A taper rate is a lateral offset over a
longitudinal run, so with both ends independently within that tolerance the
construction contributes √2 × 0.05 / L to the rate:

| taper length | from construction | as a share of the 30 km/h threshold |
|---|---|---|
| 14.9 m | 0.0047 | 2.8% |
| 20 m | 0.0035 | 2.1% |
| 34.3 m | 0.0021 | 1.2% |
| 48.4 m | 0.0015 | 0.8% |

**The measurement is the larger term.** Three captures from one viewpoint
give 0.080, 0.068, 0.062 - a standard deviation of 0.0092, which is 1.9
times the construction contribution and 5.3% of the threshold. Under
JCGM 106 that means the guard band is set by how well this pipeline
measures, not by how well the line was painted. **To make more verdicts
decidable, improve the measurement; asking for better painting would not
help.**

With a k = 2 band of ±0.018:

| posted | threshold | decides "within" below | decides "steeper" above | measured 0.070 |
|---|---|---|---|---|
| 30 km/h | 0.172 | 0.154 | 0.191 | **within reference** |
| 50 km/h | 0.062 | 0.044 | 0.080 | **indeterminate** |

At the 30 posted during the works the taper is inside the reference and the
call can be made. At the 50 the road carried before them it cannot: 0.070
sits between 0.044 and 0.080, and this measurement is not good enough to
say. That is the honest answer and the guard band is what produces it -
without one, 0.070 against 0.062 would have been reported as a breach.

The band rests on three measurements from one viewpoint, which is thin. It
will move when the pipeline is exercised on more.

## Two earlier failures it explains

**§3.3.2 puts line width within ±6mm**, so a 20 cm chevron arm varies by
±3% as laid. Arm widths measured here ranged from 7.6 to 30.7 px across
captures of the same arms - a factor of four. All of that was measurement,
none of it paint, which is why arm width was abandoned as a scale.

**§3.3.1 allows ±5cm over a 3 m longitudinal marking**, ±1.7%. So scaling
from §182's 4 m lane dash is sound in principle: the paint is accurate
enough. What failed was telling a whole dash from a continuous line or a
fragment, which is a detection problem and remains open.

## Still unresolved

Whether 臺北市's chapter binds work on a 新北市 縣道. The 公共工程施工綱要規範
is a national framework each authority adopts with local edits, and 新北市's
own version has not been read. The figures above are used as the best
available external basis and labelled as 臺北市's, not as the law here.

## Corroborated by a central agency

The concern above - that these are 臺北市's figures and the site is a 新北市
縣道 - is largely answered. 交通部高速公路局 施工技術規範, 107/03, the same
chapter 02898, §3.1(7):

> (7) 標繪標線之容許誤差規定如下︰
> A. 標線長度︰每一縱向 4 m 標線之容許誤差為±5 cm。
> B. 標線寬度︰標線寬度之容許誤差為±6 mm。
> C. …心間距，其容許誤差為±5 cm。
> **D. 標線位置︰標線之橫向位置應按設計圖所示位置，其容許誤差為±5 cm。**

Four figures, identical to 臺北市's: ±5 cm, ±6 mm, ±5 cm, ±5 cm. A central
agency in 107/03 and a city in 111/04, seven years and two independent
documents apart. **The ±5 cm is the national template value, not a Taipei
one**, and the guard band does not rest on a jurisdiction the site is not in.

The one difference is the length clause - 高公局 measures it over 4 m,
臺北市 over 3 m - and that is not the clause used here.

Full text at `docs/source-02898-freeway.txt`.

臺南市's 104 edition was checked as a third point and does not corroborate,
because it is a different and older document: materials and testing, with
only 寬度（公差 3%）in §3.8 and no geometric tolerance section at all. Its
absence is not disagreement.

新北市's own edition was not found.
