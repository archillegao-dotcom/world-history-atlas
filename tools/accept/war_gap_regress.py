"""1808 华沙公国和 2022-03-15 库皮扬斯克的边界、邻近点和生效日回归。

不改 war_audit.py 里的 86 条。这里多查生效前一天、生效当天、结束后一天，以及不该被划进去的邻近城市。
用法：python3 tools/accept/war_gap_regress.py
"""
import json
import lzma
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[2]
B = "http://127.0.0.1:8792"
fails = []


def check(name, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + f"{name} → {got}", flush=True)
    if not ok:
        fails.append(name)


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=300))


def panel(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    d = get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=p["fid"]) if p else {}
    st = d.get("state") or {}
    nm = get(f"/api/snapshot_names/{loc['snapshot']}", date=date).get(str(p.get("fid")), {}) if p else {}
    label = nm.get("zh") or st.get("name") or ""
    return f"{label}|{st.get('name') or ''}", st.get("id"), p.get("BORDERPRECISION")


def occupied(date, lat, lon):
    L = get("/api/layers/war_fronts", date=date)
    pt = Point(lon, lat)
    return any(
        shape(z["geom"]).covers(pt)
        for w in L["items"]
        for z in w["items"]
        if z["kind"] == "occupied" and z.get("geom")
    )


def offline():
    g7 = shape(json.loads((ROOT / "data/curated/geom/duchy_warsaw_1807.geojson").read_text())["geometry"])
    g9 = shape(json.loads((ROOT / "data/curated/geom/duchy_warsaw_1809.geojson").read_text())["geometry"])
    cities = {
        "华沙": (21.01, 52.23), "波兹南": (16.93, 52.41), "卡利什": (18.09, 51.76),
        "比得哥什": (18.01, 53.12), "托伦": (18.60, 53.01), "沃姆扎": (22.06, 53.18),
        "柏林": (13.40, 52.52), "柯尼斯堡": (20.51, 54.71), "但泽": (18.65, 54.35),
        "弗罗茨瓦夫": (17.04, 51.11), "比亚韦斯托克": (23.16, 53.13), "维尔纽斯": (25.28, 54.69),
    }
    for name, (lo, la) in cities.items():
        inside = name in ("华沙", "波兹南", "卡利什", "比得哥什", "托伦", "沃姆扎")
        check(f"1807线 {name}", g7.covers(Point(lo, la)), inside)
        check(f"1809线 {name}", g9.covers(Point(lo, la)), inside)
    for name, (lo, la) in {"克拉科夫": (19.94, 50.06), "卢布林": (22.57, 51.25), "拉多姆": (21.15, 51.40)}.items():
        check(f"1807线不含 {name}", g7.covers(Point(lo, la)), False)
        check(f"1809线含 {name}", g9.covers(Point(lo, la)), True)
    check("1809线不含利沃夫", g9.covers(Point(24.03, 49.84)), False)
    gap = shape(json.loads(lzma.open(ROOT / "data/war_fronts/russo_ukrainian_war/kupiansk_gap_202203.json.xz").read())["occupied"])
    check("缺口盖住库皮扬斯克", gap.covers(Point(37.61, 49.71)), True)
    check("缺口不含哈尔科夫", gap.covers(Point(36.23, 49.99)), False)
    check("缺口不含伊久姆", gap.covers(Point(37.274, 49.195)), False)
    check("缺口不含沃夫昌斯克", gap.covers(Point(36.946, 50.288)), False)
    # 约 19 平方公里，不是单点，也不是整州
    km2 = gap.area * (111.32 ** 2) * __import__("math").cos(__import__("math").radians(49.72))
    check("缺口面积在 10 到 40 平方公里", 10 < km2 < 40, True)


def live():
    def has_duchy(date, lat, lon, want):
        names, qid, prec = panel(date, lat, lon)
        got = ("华沙公国" in names) and qid == "Q152115"
        check(f"{date} ({lat},{lon}) 华沙公国", got, want)
        if want and prec != 1:
            check(f"{date} 边界精度大致", prec, 1)

    has_duchy("1807-07-08", 52.23, 21.01, False)
    has_duchy("1807-07-09", 52.23, 21.01, True)
    has_duchy("1808-07-01", 52.23, 21.01, True)
    has_duchy("1808-07-01", 52.41, 16.93, True)     # 波兹南
    has_duchy("1808-07-01", 50.06, 19.94, False)    # 克拉科夫
    has_duchy("1808-07-01", 53.13, 23.16, False)    # 比亚韦斯托克
    has_duchy("1808-07-01", 54.35, 18.65, False)    # 但泽
    has_duchy("1808-07-01", 52.52, 13.40, False)    # 柏林
    has_duchy("1809-10-13", 50.06, 19.94, False)
    has_duchy("1809-10-14", 50.06, 19.94, True)
    has_duchy("1809-10-14", 49.84, 24.03, False)    # 利沃夫
    has_duchy("1815-06-08", 52.23, 21.01, True)
    has_duchy("1815-06-09", 52.23, 21.01, False)
    names, qid, _ = panel("1820-07-01", 52.23, 21.01)
    check("1820 华沙仍是波兰或俄罗斯", any(x in names for x in ("波兰", "俄罗斯")), True)
    check("1820 华沙不再是华沙公国条目", qid != "Q152115", True)

    def occ(date, lat, lon, want, why):
        check(why, occupied(date, lat, lon), want)

    occ("2022-03-01", 49.71, 37.61, True, "03-01 库皮扬斯克在评估内")
    occ("2022-03-02", 49.71, 37.61, True, "03-02 库皮扬斯克补上")
    occ("2022-03-15", 49.71, 37.61, True, "03-15 库皮扬斯克在控制区内")
    occ("2022-03-22", 49.71, 37.61, True, "03-22 库皮扬斯克仍补上")
    occ("2022-03-23", 49.71, 37.61, True, "03-23 回到当日评估")
    occ("2022-02-24", 49.71, 37.61, False, "02-24 库皮扬斯克尚未占领")
    occ("2022-10-01", 49.71, 37.61, False, "10-01 库皮扬斯克已收复")
    occ("2022-03-15", 46.64, 32.61, True, "03-15 赫尔松仍在")
    occ("2022-03-15", 50.45, 30.52, False, "03-15 基辅不在")
    occ("2022-03-15", 49.993, 36.230, False, "03-15 哈尔科夫不在")
    occ("2022-03-15", 49.195, 37.274, False, "03-15 伊久姆不在")
    occ("2022-03-15", 50.288, 36.946, False, "03-15 沃夫昌斯克这次不补")


if __name__ == "__main__":
    offline()
    live()
    print(f"FAILURES {len(fails)}")
    sys.exit(1 if fails else 0)
