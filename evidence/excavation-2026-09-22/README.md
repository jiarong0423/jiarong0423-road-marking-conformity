# 道路挖掘許可,2026-09-22 抓取

`cases_near_116.csv` —— **13 列**,自新北市政府道路挖掘資訊篩出:
距拍攝點 400 公尺內、或 digsite/road 命中「樹林區…中正」的案件。

## 為什麼不放全檔

原始檔 **2222 列、34 欄**,其中八欄是個人資料:

```
construction_man / construction_localcallservice / construction_tel_ext
construction_mobiletelephone
supervise_man / supervise_localcallservice / supervise_tel_ext
supervise_mobiletelephone
```

`construction_mobiletelephone` 與 `supervise_mobiletelephone` 是**工地負責人
與監造人的個人手機號碼**,兩千多筆。那是政府開放資料,但把它原封放進一個
公開 repo 是另一回事 —— 這個專案已經為了五張車牌刪掉重建過一次 repo
(見 `evidence/field-2026-09-20/README.md` 與 `results/plate_redactions.json`)。

**這八欄在本檔中已移除。** 其餘欄位是案號、許可證號、工程名稱、地點、
面積、期間、工期、施工與監造「單位」(法人,非個人)、審查單位、座標。

## 來源與可回溯性

| | |
|---|---|
| 資料集 | data.gov.tw 122989 新北市政府道路挖掘資訊 |
| 端點 | `https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv/file` |
| 抓取 | 2026-09-22 |
| 全檔 | 2222 列,sha256 `15f48dc9ecc0362b2edec1d23ff6d51ee60d553389919a068762edeaad8b038d` |
| 本子集 | 13 列,sha256 `3d2eb11ecc74ac79ff2e465bbfcb8af516ded07f42373fc000b414a0a474d397` |

**端點是即時的。重抓不會得到同一份位元組**,所以全檔的 sha256 是
「當時抓到什麼」的憑證,不是可重現的把手。全檔本身**不在這個 repo 裡,
也不應該放進來**,理由如上。

## 這批資料支撐哪一項主張

管(二-3)「樹林區中正路及大安路管線工程(配合捷運管遷)」,
許可證 新北捷五所字第1140874494號,柏油長 750 公尺寬 3 公尺,
2025-05-06 至 2026-09-30。**三公尺寬七百五十公尺長就是一整條車道。**

拍照當天生效的是第 7 次變更,日間 09 時至 16 時;照片 EXIF 15:56–16:01。

它**沒有**證明那條溝延伸到拍攝點:登記點距拍攝點 1892 公尺,溝渠 750 公尺。
能定案的是該許可的施工圖說或交通局的交通維持計畫。見 `results/excavation_live_2026-09-22.json`。
