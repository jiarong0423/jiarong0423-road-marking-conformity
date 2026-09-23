> **Historical working note (content from 2026-09-20).** Numbers and status here may be superseded. The current account is [`technical-report.md`](technical-report.md); withdrawn figures are listed there.

# What the authorities actually record

Written 2026-09-20. Every number here came from a public endpoint that the
scripts in this repository can call again; none of it is estimated from an
image.

## The route

新北市政府養護工程處, 《新北市公路系統明細》 (PDF, 養工處 downloaddata
202101081434300):

| 序號 | 公路編號 | 起地點樁號 | 訖地點樁號 | 合計里程 |
|---|---|---|---|---|
| 20 | 116 | 台1線14K+460 (萬壽路一段) | 台3線11K+669 (中央路一段) | 5.357 km |

The same table places `116線0K+447(中正路)` and `116線0K+795(中正路、三德街)`,
which is how the site is addressed in any correspondence: by chainage on 116,
not by a coordinate.

**The table has four columns and none of them is width.** 序號, 公路編號,
起地點樁號, 訖地點樁號, 合計里程. Road width is not in this record. A
secondary source gives 中正路 as 30 m wide with six lanes, but it carries no
footnote, so it is not used here for anything.

## The bridges

新北市轄內橋梁基本資料 (data.ntpc.gov.tw, dataset
38061b5c-165e-48bf-baec-158dbd5b2c52). Fields: itemno, bridgename, county,
town, grade, length, head/end longitude and latitude.

**No width field, and no lane count.** Within 1 km of the site:

| distance | bridge | grade | length |
|---|---|---|---|
| 430 m | 樹林陸橋2B-2(A) | 市道 | 355.6 m |
| 742 m | 十三公橋 | 市道 | 15.1 m |
| 809 m | 樹林陸橋2B-2(B) | 市道 | 18.5 m |
| 821 m | 光武橋 | 市道 | 7 m |

So the answer to whether the maintenance office records road width and area
including bridges is: it records **length** and **excavated area**, and it does
not record **width** for either the carriageway or the bridges.

## The excavations

新北市政府道路挖掘資訊 (dataset 96b6101b-c033-4834-8bd5-e312651db7a0),
2,216 cases, 民國1111212 to 民國1151116 (2022-12-12 to 2026-11-16). This
dataset *does* carry area: `digarea` gives length, width, depth and total per
case, plus `constructionunit`, `supervise`, start and end dates and TWD97
coordinates.

The largest case on 中正路 is:

    案 335384  樹林區中正路及大安路管線工程-管(二-3)(配合捷運管遷)
    施工 福旺營造股份有限公司 / 監造 台灣自來水公司第十二區管理處
    柏油, 長 750 m, 寬 3 m, 深 1.2 m, 面積 2,250 m²
    民國114-05-06 起, 原訂 179 日, 展延七次, 至 115-09-30

A 3 m wide trench running 750 m is one lane's worth of carriageway, and it
would be the obvious explanation for a lane closure. **It is not the
explanation here.** Its registered point converts to 25.0150802, 121.4108366,
which is 1,828 m from the site; with a 750 m run its near end is still some
1,450 m away.

Every case within 400 m of the site, regardless of road name:

| distance | dates | total area | case |
|---|---|---|---|
| 25 m | 2026-03-12~08-18 | 4.5 m² | 人手孔蓋升降及周邊加固 |
| 242 m | 2026-09-22~09-30 | 8 m² | 交通局交通管制工程科 |
| 267 m | 2026-07-16~08-23 | 70.2 m² | 69kV 樹德~江翠管路工程 |
| 357 m | 2026-07-24~08-25 | 280 m² | 台灣電力公司 |
| 361 m | 2026-04-20~08-28 | 7.8 m² | 樹林區文林段污水管遷工程 |

**None of these can close a lane**, and the dataset's coverage begins
2022-12-12, which is within weeks of the November 2022 start already on the
timeline. So the works at this location are not in the excavation permit
record at all.

Three readings, none of them yet checked:

1. the works are permitted as 道路工程 rather than 道路挖掘, which is a
   different register;
2. the authority is 新北捷運局 rather than 養護工程處, so they do not appear in
   養工處's dataset;
3. there is no excavation, and the narrowing is a marking change, which needs
   no dig permit.

Reading 3 would matter most to this project, because it would mean the taper
was drawn rather than forced. It is not evidence for that yet - an absence in
one register is an absence in one register.

## The imagery

內政部國土測繪中心 WMTS serves national orthophoto as PHOTO2014 … PHOTO2025.
At zoom 20 and this latitude the ground sample is **0.1353 m/px**, and the
image is already orthorectified: there is no camera pose to estimate, no
horizon to find and no vanishing point to recover. This removes the failure
documented in `thesis.md`, where line groups were sorted by angle window and
the pipeline printed 18.3 km/h for a photograph it should have declined.

The twelve layer names resolve to **eight distinct images** - PHOTO2015 and
PHOTO2016 are byte-identical, as are 2019/2020, 2021/2022, 2023/2024 and
2025/PHOTO2. The layer name is a publication year, not a flight date, so
"PHOTO2022" may well predate the November 2022 start.

What this resolution can and cannot carry:

- a 3 m lane is 22 px, and a 20 m taper is 148 px - both measurable;
- a 15 cm edge line is 1 px, so §171 line widths **cannot** be measured here
  and must still come from the field photographs.

The three epochs are not co-registered; building footprints shift between
them. Comparing them requires registration first, which is not done yet.
