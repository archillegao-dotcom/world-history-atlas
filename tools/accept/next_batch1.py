"""第一批：1950-03-16 李弥部活动层，以及 1930-11-08 同政权多块联动的数据前提。

用法：WHA_PORT=8792 python3 tools/accept/next_batch1.py
联动的高亮在浏览器脚本里查。这里确认日期、几何和政权编号。
"""
import json, os, sys, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=300))


def regime(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    if not p:
        return {"poly": None, "qid": None, "name": None, "fid": None}
    d = get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=p["fid"])
    st = d.get("state") or {}
    return {"poly": p.get("NAME"), "qid": st.get("id"), "name": st.get("name"), "fid": p.get("fid")}


def zones(date):
    return get("/api/layers/control_zones", date=date)["items"]


def one(items, needle):
    return next((i for i in items if needle in i["name"] or needle in i.get("id", "")), None)


fails = []


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:220])
    if not cond:
        fails.append(label)


def pip(geom, lon, lat):
    """射线法，只用于这些简单多边形。"""
    if geom["type"] == "MultiPolygon":
        return any(pip({"type": "Polygon", "coordinates": c}, lon, lat) for c in geom["coordinates"])
    ring = geom["coordinates"][0]
    inside = False
    x, y = lon, lat
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


mar = zones("1950-03-16")
box = one(mar, "kmt_kengtung_tachileik_1950")
check("1950-03-16 有景栋至大其力活动层", bool(box) and "云南反共救国军" in box["name"] and "李弥" in box["name"], (box or {}).get("name"))
check("这一层写明不是疆域也不是云南全省", bool(box) and "不是疆域" in (box or {}).get("note", "") and "不是云南" in (box or {}).get("note", ""), (box or {}).get("note"))
pts = {p["name_zh"]: p for p in (box or {}).get("activity_points") or []}
check("活动点是景栋和大其力", set(pts) == {"景栋", "大其力"}, sorted(pts))
check("景栋坐标来自记载的城镇点", abs(pts.get("景栋", {}).get("lat", 0) - 21.29167) < 1e-4 and abs(pts.get("景栋", {}).get("lon", 0) - 99.60833) < 1e-4, pts.get("景栋"))
check("大其力坐标来自记载的城镇点", abs(pts.get("大其力", {}).get("lat", 0) - 20.45278) < 1e-4 and abs(pts.get("大其力", {}).get("lon", 0) - 99.89583) < 1e-4, pts.get("大其力"))
check("包络不是活动点独占的占位", bool(box) and not box.get("activity_only"), box.get("activity_only") if box else None)
check("昆明不在包络里", bool(box) and not pip(box["geom"], 102.68, 25.04), "kunming")
check("昆明仍是中华人民共和国", regime("1950-03-16", 25.04, 102.68)["qid"] == "Q148", regime("1950-03-16", 25.04, 102.68))
check("景栋一带点击不是中华民国主权", (regime("1950-03-16", 20.8, 99.3)["qid"] or "") not in ("Q865", "Q13426199"), regime("1950-03-16", 20.8, 99.3))
check("1949-12-31 还没有这层", not any("李弥" in i["name"] for i in zones("1949-12-31")), "dec")
feb = zones("1950-02-01")
check("1950-02-01 只有大其力活动点", any(i["id"] == "kmt_tachileik_1950" for i in feb) and not any(i["id"] == "kmt_kengtung_tachileik_1950" for i in feb), [i["id"] for i in feb if "kmt_" in i["id"]])
jul = zones("1950-07-01")
check("1950-07-01 改标孟萨活动点", any(i["id"] == "kmt_monghsat_1950_1961" for i in jul) and not any(i["id"] == "kmt_kengtung_tachileik_1950" for i in jul), [i["id"] for i in jul if "kmt_" in i["id"]])
y51 = zones("1951-06-01")
limi = next((i for i in y51 if "李弥" in i["name"]), None)
check("1951年图层仍有李弥部且写明不是全省主权", bool(limi) and "不是主权" in (limi.get("note") or "") and "不是云南" in (limi.get("note") or ""), (limi or {}).get("note"))
check("1961-04-16 孟萨活动点还在", any(i["id"] == "kmt_monghsat_1950_1961" for i in zones("1961-04-16")), "apr16")
check("1961-04-17 起不再画李弥部", not any("李弥" in i["name"] for i in zones("1961-04-17")), [i["name"] for i in zones("1961-04-17") if "李弥" in i["name"] or "云南反共" in i["name"]])

# 1930-11-08：本土、南桦太、千岛是同一个政权编号，朝鲜日治和台湾日据不是。
JP = "Q188712"
tokyo = regime("1930-11-08", 35.68, 139.69)
kara = regime("1930-11-08", 46.96, 142.73)
itu = regime("1930-11-08", 45.05, 147.8)
kuna = regime("1930-11-08", 44.07, 145.85)
para = regime("1930-11-08", 50.4, 155.9)
seoul = regime("1930-11-08", 37.57, 126.98)
taipei = regime("1930-11-08", 25.04, 121.56)
check("东京是大日本帝国", tokyo["qid"] == JP and tokyo["fid"], tokyo)
check("南桦太是大日本帝国且不是东京那一块", kara["qid"] == JP and kara["fid"] and kara["fid"] != tokyo["fid"], kara)
check("择捉是大日本帝国且单独成块", itu["qid"] == JP and itu["poly"] == "Kuril Islands" and itu["fid"] not in (tokyo["fid"], kara["fid"]), itu)
check("国后是大日本帝国", kuna["qid"] == JP and kuna["fid"] == itu["fid"], kuna)
check("幌筵不再落在苏联多边形上", para["qid"] == JP and para["fid"] == itu["fid"], para)
check("朝鲜日治不是大日本帝国这一编号", seoul["qid"] == "Q503585" and seoul["fid"] not in (tokyo["fid"], kara["fid"], itu["fid"]), seoul)
check("台湾日据不是大日本帝国这一编号", taipei["qid"] == "Q137816", taipei)
check("1886-01-01 择捉已是大日本帝国", regime("1886-01-01", 45.05, 147.8)["qid"] == JP, regime("1886-01-01", 45.05, 147.8))
check("1945-09-04 择捉仍是大日本帝国", regime("1945-09-04", 45.05, 147.8)["qid"] == JP, regime("1945-09-04", 45.05, 147.8))
check("1945-09-05 起整链不再标成日本", regime("1945-09-05", 45.05, 147.8)["qid"] != JP, regime("1945-09-05", 45.05, 147.8))

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
