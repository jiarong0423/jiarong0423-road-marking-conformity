"""When is a low sun ahead of a rider on this stretch? (isolation, 2026-09-23)

Owner: 夜間、早晨、逆光. Night has no evidence yet; glare is geometry.
NOAA solar position (the standard approximation, ~0.5 deg). Site from
output/seq/+0035.5.json (25.00271, 121.42377). Road bearing 141.6 deg towards the
bridge (Street View heading along the axis), 321.6 away from it.
Glare window: sun elevation 0-15 deg and within +-25 deg of the travel bearing.
"""
import math, datetime as dt

LAT, LON, TZ = 25.00271, 121.42377, 8
BEARINGS = {"往橋頭 141.6°": 141.6, "離開橋頭 321.6°": 321.6}


def sun(t):
    d = t - dt.datetime(2000, 1, 1, 12) - dt.timedelta(hours=TZ)
    n = d.total_seconds() / 86400
    L = (280.460 + 0.9856474 * n) % 360; g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)); eps = math.radians(23.439 - 4e-7 * n)
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam)); dec = math.asin(math.sin(eps) * math.sin(lam))
    gmst = (280.46061837 + 360.98564736629 * n) % 360
    H = math.radians((gmst + LON) % 360) - ra; la = math.radians(LAT)
    el = math.asin(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(H))
    az = math.atan2(-math.sin(H), math.tan(dec) * math.cos(la) - math.sin(la) * math.cos(H))
    return math.degrees(el), math.degrees(az) % 360


def diff(a, b):
    return abs((a - b + 180) % 360 - 180)


if __name__ == "__main__":
    for hh, mm in [(6, 30), (6, 34), (6, 45), (7, 0), (7, 30)]:
        el, az = sun(dt.datetime(2026, 9, 23, hh, mm))
        print(f"2026-09-23 {hh:02d}:{mm:02d}  仰角 {el:5.1f}°  方位 {az:5.1f}°  與往橋頭方向差 {diff(az, 141.6):5.1f}°")
    print()
    for name, b in BEARINGS.items():
        days = {}
        for doy in range(365):
            day = dt.datetime(2026, 1, 1) + dt.timedelta(days=doy)
            for minute in range(5 * 60, 19 * 60, 5):
                t = day + dt.timedelta(minutes=minute); el, az = sun(t)
                if 0 < el <= 15 and diff(az, b) <= 25:
                    days.setdefault(day.date(), []).append(t.strftime("%H:%M"))
        if not days:
            print(name, "全年沒有低角度正面陽光"); continue
        ds = sorted(days)
        print(name, f"全年 {len(ds)} 天有低角度陽光在前方 ±25°;第一天 {ds[0]} 最後一天 {ds[-1]}")
        for d in ds[::max(1, len(ds) // 6)]:
            print("   ", d, days[d][0], "–", days[d][-1])
