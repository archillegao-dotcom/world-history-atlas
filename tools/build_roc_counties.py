#!/usr/bin/env python3
"""把关内手绘占领框换成 1931 年治所的泰森多边形。

治所：MCGD_Rep V2（Zenodo 5721459，CC BY 4.0，Christian Henriot / ENP-China）。
每个县域是该治所的 Voronoi 单元，再裁到 ENP-China 历史省多边形上。
省多边形的外缘就是这套图的海岸。没有使用 CHGIS。

用法：python3 tools/build_roc_counties.py
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

from shapely.geometry import MultiPoint, Point, mapping, shape
from shapely.ops import voronoi_diagram
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.build_control_zones import resolve  # noqa: E402

CSV_SRC = Path("/tmp/wha-mcgd/MCGD_Rep_V2.csv")
CSV_DST = ROOT / "data" / "curated" / "geom" / "MCGD_Rep_V2.csv"
CELLS = ROOT / "data" / "curated" / "geom" / "roc_county_cells.geojson"
EXTENTS = ROOT / "data" / "curated" / "geom" / "roc_cell_extents.json"
ZONES = ROOT / "data" / "curated" / "control_zones.json"
BEIYANG = ROOT / "data" / "curated" / "roc_beiyang.json"
GEOM = ROOT / "data" / "curated" / "roc_admin_geom.json"
PHRASE = "大致。县域为治所泰森多边形近似。"

# 1933 年非武装区两专区的 22 县。冀东防共自治政府辖这 22 县。
# https://zh.wikipedia.org/wiki/冀东防共自治政府
EAST_HEBEI = [
    "盧龍", "遷安", "撫寧", "昌黎", "灤縣", "樂亭", "臨榆", "豐潤", "寧河",
    "通縣", "三河", "寶坻", "薊縣", "香河", "昌平", "順義", "密雲", "懷柔", "平谷", "遵化", "興隆", "玉田",
]
# 1934 年 9 月记载里剩下的八个县城。
SOVIET = ["瑞金", "會昌", "雩都", "興國", "寧都", "石城", "寧化", "長汀"]
# 占领层不得早于这些点。坐标与 tools/accept/occupation_fall.py 相同。
CITIES = [
    ("上海", 121.477, 31.233, "1937-11-12"),
    ("南京", 118.8, 32.06, "1937-12-13"),
    ("太原", 112.587, 37.839, "1937-11-08"),
    ("徐州", 117.257, 34.302, "1938-05-19"),
    ("武汉", 114.3, 30.59, "1938-10-25"),
    ("广州", 113.264, 23.122, "1938-10-21"),
    ("长沙", 112.971, 28.197, "1944-06-18"),
    ("桂林", 110.29, 25.27, "1944-11-09"),
    ("杭州", 120.169, 30.294, "1937-12-24"),
    ("苏州", 120.614, 31.318, "1937-11-19"),
    ("青岛", 120.038, 36.274, "1938-01-10"),
    ("厦门", 118.077, 24.460, "1938-05-13"),
    ("无锡", 120.291, 31.583, "1937-11-25"),
    ("常州", 119.943, 31.765, "1937-11-29"),
    ("芜湖", 118.370, 31.342, "1937-12-10"),
    ("济南", 116.998, 36.690, "1937-12-27"),
    ("开封", 114.345, 34.802, "1938-06-06"),
    # 治所点。九江、镇江的单元格在更晚的色块里，从沦陷日起补到那一块。
    ("九江", 116.04059, 29.71584, "1938-07-26"),
    ("镇江", 119.45471, 32.19607, "1937-12-08"),
]
# 从沦陷日起另画、并且要写明收到哪一天的单元格。until 为空则收到下一块盖住这里的日期；没有下一块就收到 1945-08-16。
# 汕头市区落在 1931 年朝阳治所的单元格里。澄海治所也在原来的汕头方框里，两格同一天，不把 3 月 27 日写成已经沦陷。
JP = {"qid": "Q188712", "zh": "大日本帝国"}
WANG = {"qid": "Q696242", "zh": "汪精卫政权"}
REFORM = {"qid": "Q708865", "zh": "中华民国维新政府"}
GROWTH = [
    ("安庆", [(117.037, 30.53782)], "1938-06-12", "1940-03-30", REFORM, "中华民国维新政府（安庆）",
     "怀宁县域。1938-06-12 安庆沦陷。6 月 6 日的色块更早，从那一块移出。1940-03-30 起改记汪精卫政权。"),
    ("安庆", [(117.037, 30.53782)], "1940-03-30", "1945-08-16", WANG, "汪精卫政权（安庆）",
     "怀宁县域。1940-03-30 起随华中日占区改记汪精卫政权，收到 1945-08-16。"),
    ("宜昌", [(111.28472, 30.70323)], "1940-06-12", "1945-08-16", WANG, "汪精卫政权（宜昌）",
     "宜昌县域。1940-06-12 沦陷。原来的手绘范围没有盖住这个治所，不把邻近县加进来。"),
    ("海口", [(110.19939, 20.05511)], "1939-02-10", "1940-03-30", JP, "日军占领区（海口）",
     "海口治所的单元格。1939-02-10 起。琼山和岛上其余县仍从 1939-03-27 的海南块起，不提前。"),
    ("海口", [(110.19939, 20.05511)], "1940-03-30", "1945-08-16", WANG, "汪精卫政权（海口）",
     "海口治所的单元格。1940-03-30 起与海南岛其余占领层一样改记汪精卫政权。"),
    ("汕头", [(116.682, 23.354), (116.72577, 23.48103)], "1939-06-21", "1940-03-30", JP, "日军占领区（汕头）",
     "汕头市区落在 1931 年朝阳治所的单元格里，澄海治所也在原来的汕头方框里。两格从 1939-06-21 起，不再从 3 月 27 日起。潮安不在这框里。"),
    ("南宁", [(108.29251, 22.80864)], "1939-11-24", "1940-11-01", JP, "日军军事占领区（南宁）",
     "邕宁县域。1939-11-24 沦陷。1940 年 10 月撤回，日没有锁，收到 11 月 1 日。1944 年 11 月的第二次占领不在这一格里。"),
    ("福州", [(119.32158, 26.07395), (119.32122, 26.09425)], "1941-04-21", "1941-09-03", JP, "日军军事占领区（福州）",
     "福州和闽侯两个治所几乎叠在一起，两格都画。1941-04-21 占领，9 月 3 日撤出。连江、长乐、福清、平潭没有并进来。"),
    ("福州", [(119.32158, 26.07395), (119.32122, 26.09425)], "1944-10-04", "1945-05-18", JP, "日军军事占领区（福州）",
     "福州、闽侯两格。1944-10-04 再沦陷，1945-05-18 光复，这一天起不再画。"),
    ("衡阳", [(112.56975, 26.93801)], "1944-08-08", "1945-08-16", WANG, "汪精卫政权（衡阳）",
     "衡阳县域。1944-08-08 沦陷。原来的湖南手绘范围没有盖住这个治所。"),
    ("柳州", [(109.26731, 24.30179)], "1944-11-11", "1945-08-16", JP, "日军军事占领区（柳州）",
     "1931 年治所仍名马平。1944-11-11 沦陷。桂柳走廊的手绘范围没有盖住这个治所，控制方沿用那一条的日军军事占领，不是汪政权。"),
]
SEA = [(122.8, 31.0), (122.6, 36.3), (120.2, 26.2), (113.8, 21.6)]
SNAP = 0.03
# MCGD 的省名和 ENP 的省名不是同一套字。只在点落在那块省界里、或离它不到 SNAP 度时才用。
PREF = {
    "遼寧": "奉天", "遼北": "奉天", "遼西": "奉天", "西康": "川邊", "海南": "廣東",
    "武漢": "湖北", "重慶市": "四川", "內蒙古": "綏遠", "松江": "吉林", "合江": "吉林", "興安": "黑龍江",
}


def load_seats():
    if not CSV_DST.exists():
        if not CSV_SRC.exists():
            raise SystemExit("missing MCGD csv")
        CSV_DST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CSV_SRC, CSV_DST)
    rows = list(csv.DictReader(CSV_DST.open(encoding="utf-8-sig")))
    seats = []
    used = set()
    for i, r in enumerate(rows):
        try:
            lon, lat = float(r["LONG"]), float(r["LAT"])
        except ValueError:
            continue
        fid = (r.get("FID") or "").strip()
        loc = (r.get("LocID") or "").strip()
        if fid and fid not in ("NA", "None"):
            cid = "mcgd:" + fid
        elif loc and loc not in ("NA", "None"):
            cid = "mcgd:" + loc
        else:
            cid = f"mcgd:{r['Name_ZhT']}-{i}"
        n = cid
        k = 2
        while n in used:
            n = f"{cid}-{k}"
            k += 1
        used.add(n)
        seats.append({
            "id": n,
            "name": r["Name_ZhT"],
            "province": r["Province_ZhT"],
            "level": r["Level"],
            "lon": lon,
            "lat": lat,
        })
    return seats


def load_provinces():
    units = json.loads(GEOM.read_text(encoding="utf-8"))["units"]
    geoms = []
    for u in units:
        if str(u["sid"]).startswith("1947-") and u["sid"] != "1947-台灣":
            continue
        g = make_valid(shape(u["geom"]))
        if g.is_empty:
            continue
        geoms.append((u["sid"], u["name_1912"], g))
    return geoms


def build_cells(seats, provinces):
    polys = [g for _, _, g in provinces]
    by_pname = {}
    for _sid, name, g in provinces:
        by_pname.setdefault(name, g)
    tree = STRtree(polys)
    points = []
    kept = []
    outside = []
    for s in seats:
        pt = Point(s["lon"], s["lat"])
        containers = []
        for i in tree.query(pt):
            g = polys[int(i)]
            if g.covers(pt):
                containers.append(provinces[int(i)])
        pref_name = PREF.get(s["province"], s["province"])
        pref = by_pname.get(pref_name)
        clip = None
        pname = None
        if pref is not None and pref.covers(pt):
            pname, clip = pref_name, pref
        elif containers:
            _sid, pname, clip = min(containers, key=lambda t: t[2].area)
        elif pref is not None and pref.distance(pt) <= SNAP:
            pname, clip = pref_name, pref.buffer(SNAP)
        else:
            nearest = min(provinces, key=lambda t: t[2].distance(pt))
            if nearest[2].distance(pt) <= SNAP:
                pname, clip = nearest[1], nearest[2].buffer(SNAP)
        if clip is None:
            outside.append(s["name"] + "/" + s["province"])
            continue
        s = dict(s)
        s["pname"] = pname
        s["prov"] = clip
        kept.append(s)
        points.append(pt)
    print("outside ENP", len(outside), " ".join(outside[:30]))
    regions = voronoi_diagram(MultiPoint(points), tolerance=0)
    geoms = list(regions.geoms)
    rtree = STRtree(geoms)
    features = []
    missed = 0
    for s in kept:
        pt = Point(s["lon"], s["lat"])
        cell = None
        for i in rtree.query(pt):
            g = geoms[int(i)]
            if g.covers(pt):
                cell = g
                break
        if cell is None:
            missed += 1
            continue
        clipped = make_valid(cell.intersection(s["prov"]))
        if clipped.is_empty or clipped.area < 1e-8:
            missed += 1
            continue
        clipped = clipped.simplify(0.001, preserve_topology=True)
        features.append({
            "type": "Feature",
            "properties": {
                "id": s["id"],
                "name": s["name"],
                "province": s["pname"],
                "level": s["level"],
                "lon": round(s["lon"], 5),
                "lat": round(s["lat"], 5),
            },
            "geometry": mapping(clipped),
        })
    print(f"seats {len(seats)} inside ENP {len(kept)} cells {len(features)} missed {missed}")
    return features


def by_name(features, names, province=None):
    found = {}
    for f in features:
        n = f["properties"]["name"]
        if n not in names:
            continue
        if province and f["properties"]["province"] != province and n in found:
            continue
        if n in found and province and f["properties"]["province"] == province:
            found[n] = f
            continue
        if n not in found:
            found[n] = f
    missing = [n for n in names if n not in found]
    if missing:
        raise SystemExit("county names missing: " + "、".join(missing))
    return [found[n]["properties"]["id"] for n in names]


def spec_blob(spec):
    return json.dumps(spec, ensure_ascii=False)


def should_convert(zone):
    if not str(zone.get("id", "")).startswith("sjw_"):
        return False
    if zone["id"] in ("sjw_manchuria_1931",) or "unverified" in zone["id"] or zone["id"].startswith("sjw_cell_"):
        return False
    blob = spec_blob(zone.get("geometry") or {})
    if "basemap" in blob or "cshapes" in blob:
        return False
    if "polygon" in blob or "roc_counties" in blob:
        return True
    return False


def cell_at(features, prepared, lon, lat):
    pt = Point(lon, lat)
    for i in prepared.query(pt):
        if features[int(i)]["geom"].covers(pt):
            return features[int(i)]["properties"]["id"]
    return None


def main():
    seats = load_seats()
    provinces = load_provinces()
    features = build_cells(seats, provinces)
    fc = {
        "type": "FeatureCollection",
        "source": {
            "seats": "MCGD_Rep V2",
            "url": "https://zenodo.org/records/5721459",
            "license": "CC BY 4.0",
            "attribution": "Christian Henriot, ENP-China. Modern China Geospatial Database, Republican China Dataset.",
            "clip": "ENP-China / Virtual Shanghai historical provinces (CC0). The province outline supplies the coastline.",
            "note": "县域为治所泰森多边形近似，不是县界，也不是 CHGIS。",
        },
        "features": features,
    }
    CELLS.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", CELLS, "bytes", CELLS.stat().st_size)

    geoms = []
    for f in features:
        g = make_valid(shape(f["geometry"]))
        f["geom"] = g
        geoms.append(g)
    tree = STRtree(geoms)
    sea_hits = []
    for lon, lat in SEA:
        cid = cell_at(features, tree, lon, lat)
        if cid:
            sea_hits.append((lon, lat, cid))
    print("sea hits", sea_hits)

    doc = json.loads(ZONES.read_text(encoding="utf-8"))
    doc["zones"] = [z for z in doc["zones"] if not str(z.get("id", "")).startswith("sjw_cell_")]
    extents = json.loads(EXTENTS.read_text(encoding="utf-8")) if EXTENTS.exists() else {}
    id_of = {f["properties"]["id"]: f for f in features}
    seat_pt = {f["properties"]["id"]: Point(f["properties"]["lon"], f["properties"]["lat"]) for f in features}

    converted = []
    for zone in doc["zones"]:
        if not should_convert(zone):
            continue
        if zone["id"] not in extents:
            if "polygon" not in spec_blob(zone.get("geometry") or {}):
                continue
            extents[zone["id"]] = zone["geometry"]
        extent = resolve(extents[zone["id"]])
        ids = []
        if zone["id"] == "sjw_east_hebei":
            ids = by_name(features, EAST_HEBEI, province="河北")
        else:
            for fid, pt in seat_pt.items():
                if extent.covers(pt):
                    ids.append(fid)
            for _name, lon, lat, _fall in CITIES:
                if extent.covers(Point(lon, lat)):
                    cid = cell_at(features, tree, lon, lat)
                    if cid and cid not in ids:
                        ids.append(cid)
        ids = sorted(set(ids))
        if not ids:
            print("EMPTY", zone["id"])
            continue
        zone["geometry"] = {"roc_counties": ids}
        note = zone.get("note") or ""
        if "泰森" not in note:
            zone["note"] = (note + " " + PHRASE).strip()
        converted.append(zone)
        print(f"{zone['id']:40} counties={len(ids):4}")

    # 城池点若落在更早的块里，从那一块拿掉，并补上从沦陷日起的县域。
    by_id = {z["id"]: z for z in converted}
    supplements = []
    for name, lon, lat, fall in CITIES:
        cid = cell_at(features, tree, lon, lat)
        if not cid:
            print("NO CELL", name)
            continue
        offenders = []
        for z in converted:
            if cid in z["geometry"]["roc_counties"] and (z.get("from") or "") < fall:
                offenders.append(z)
        for z in offenders:
            z["geometry"]["roc_counties"] = [i for i in z["geometry"]["roc_counties"] if i != cid]
        starters = [z for z in converted if cid in z["geometry"]["roc_counties"] and (z.get("from") or "") >= fall]
        if starters and min(z["from"] for z in starters) <= fall:
            continue
        gap_until = min((z["from"] for z in starters), default=None)
        if gap_until is None:
            if not offenders:
                print("UNCOVERED", name, cid)
                continue
            gap_until = max(z.get("until") or "1945-08-16" for z in offenders)
        src = offenders[0] if offenders else starters[0]
        sid = f"sjw_cell_{cid}_{fall}_{name}"
        if any(z["id"] == sid for z in doc["zones"]):
            continue
        supplements.append({
            "id": sid,
            "group": "sino_japanese_war",
            "kind": "occupied",
            "as_polity": True,
            "name_zh": src["name_zh"],
            "name_en": src.get("name_en") or src["name_zh"],
            "controller": src["controller"],
            "from": fall,
            "until": gap_until,
            "geometry": {"roc_counties": [cid]},
            "approx": True,
            "note": f"{name}县域。{PHRASE}不把沦陷日之前的色块扩到这个治所。未核对《中華民國史事紀要》。",
            "dates_note": f"{name} {fall} 起，收到下一块盖住这里的日期。",
            "sources": src.get("sources") or [],
        })
        print("supplement", name, fall, gap_until, cid)
    for s in supplements:
        if s["id"].endswith("_徐州"):
            s["note"] = (
                "徐州县域。已核對《中華民國史事紀要》民國二十七年一月至六月，"
                "印页四七九（PDF 第483页），页眉民国二十七年五月十八、十九日，写至十时徐州失守。"
                "6月6日起并入后面那一块。" + PHRASE
            )
            s["dates_note"] = "徐州 1938-05-19 起，收到 1938-06-06。已核對《中華民國史事紀要》印页四七九。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13313.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_镇江"):
            s["note"] = (
                "镇江县域。江苏省志大事年表写1937年12月8日镇江、靖江失陷。"
                "12月6日天谷支队的说法没有并成这一天。12月14日起并入南京那一块。"
                + PHRASE + "未核对《中華民國史事紀要》。"
            )
            s["dates_note"] = "镇江 1937-12-08 起，收到 1937-12-14。"
            s["sources"] = [
                "https://web.archive.org/web/20170809172042/http://www.jssdfz.gov.cn/book/jsz2/FL/FL.html",
                "http://lyj.jiangsu.gov.cn/art/2021/4/21/art_81813_9762633.html",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_桂林"):
            s["note"] = (
                "桂林县域。已核對《中華民國史事紀要》民國三十三年十月至十二月，"
                "印页三七五（PDF 第383页），页眉民国三十三年十一月九日，写广西桂林本日为日军突入。"
                "1944-11-10 起并入桂柳走廊那一块。走廊其余县不提前到这一天。" + PHRASE
            )
            s["dates_note"] = (
                "桂林 1944-11-09 起，收到 1944-11-10。已核對《中華民國史事紀要》印页三七五。"
                "原图是 1944-11-10，改到这一天。"
            )
            s["name_zh"] = "日军军事占领区（桂林）"
            s["name_en"] = "日军军事占领区（桂林）"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13334.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_九江"):
            s["note"] = (
                "九江县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页一五九（PDF 第167页），页眉民国二十七年七月二十五、二十六日，写二十六日九江陷落。"
                "1939-03-27 起并入已经盖住这里的占领层。" + PHRASE
            )
            s["dates_note"] = "九江 1938-07-26 起，收到 1939-03-27。已核對《中華民國史事紀要》印页一五九。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
    doc["zones"].extend(supplements)

    for name, points, fall, end, controller, name_zh, why in GROWTH:
        ids = []
        for lon, lat in points:
            cid = cell_at(features, tree, lon, lat)
            if cid and cid not in ids:
                ids.append(cid)
        if len(ids) != len(points):
            print("NO CELL", name, ids)
            continue
        for z in converted:
            if (z.get("from") or "") < fall and any(i in z["geometry"]["roc_counties"] for i in ids):
                z["geometry"]["roc_counties"] = [i for i in z["geometry"]["roc_counties"] if i not in ids]
                print("strip", name, z["id"])
        sid = f"sjw_cell_{'_'.join(i.split(':')[-1] for i in ids)}_{fall}_{name}"
        if any(z["id"] == sid for z in doc["zones"]):
            continue
        supplements_extra = {
            "id": sid,
            "group": "sino_japanese_war",
            "kind": "occupied",
            "as_polity": True,
            "name_zh": name_zh,
            "name_en": name_zh,
            "controller": controller,
            "from": fall,
            "until": end,
            "geometry": {"roc_counties": ids},
            "approx": True,
            "note": f"{why} {PHRASE}未核对《中華民國史事紀要》。",
            "dates_note": f"{name} {fall} 起，收到 {end}。",
            "sources": {
                "安庆": ["https://zh.wikipedia.org/wiki/武汉会战", "https://zenodo.org/records/5721459"],
                "宜昌": ["https://zh.wikipedia.org/wiki/枣宜会战", "https://zenodo.org/records/5721459"],
                "海口": ["https://zh.wikipedia.org/wiki/日本侵佔海南島", "https://zenodo.org/records/5721459"],
                "汕头": [
                    "https://www.shantou.gov.cn/stszrzyj/zwgk/gzdt/content/post_2449128.html",
                    "https://daj.shantou.gov.cn/daj/kzda/201506/7f8b9a33ebf04ed8bb12c0cbecc8b78d.shtml",
                    "https://zenodo.org/records/5721459",
                ],
                "南宁": ["https://zh.wikipedia.org/wiki/桂南会战", "https://zenodo.org/records/5721459"],
                "福州": ["http://fz.fjdsfzw.org.cn/2015-11-19/content_85283.html", "https://zenodo.org/records/5721459"],
                "衡阳": ["https://zh.wikipedia.org/wiki/衡阳保卫战", "https://zenodo.org/records/5721459"],
                "柳州": ["https://zh.wikipedia.org/wiki/桂柳会战", "https://zenodo.org/records/5721459"],
            }[name],
        }
        if name == "柳州":
            supplements_extra["note"] = (
                "1931 年治所仍名马平。已核對《中華民國史事紀要》民國三十三年十月至十二月，"
                "印页四二三（PDF 第431页），页眉民国三十三年十一月十一日，写广西柳州本日为日军攻占，"
                "并写柳州继桂林失陷。桂柳走廊的手绘范围没有盖住这个治所，"
                "控制方沿用那一条的日军军事占领，不是汪政权。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "柳州 1944-11-11 起，收到 1945-08-16。已核對《中華民國史事紀要》印页四二三。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13334.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "海口" and fall == "1939-02-10":
            supplements_extra["note"] = (
                "海口治所的单元格。已核對《中華民國史事紀要》民國二十八年一月至六月，"
                "印页二二〇（PDF 第220页），页眉民国二十八年二月十日，写海口于下午三时陷敌。"
                "琼山和岛上其余县仍从 1939-03-27 的海南块起，不提前。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "海口 1939-02-10 起，收到 1940-03-30。已核對《中華民國史事紀要》印页二二〇。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13315.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        doc["zones"].append(supplements_extra)
        print("growth", name, fall, end, ids)

    harbin = "mcgd:s417"
    if harbin in id_of and not any(z["id"] == "ccw_harbin_1946" for z in doc["zones"]):
        doc["zones"].append({
            "id": "ccw_harbin_1946",
            "group": "ccw_manchuria",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "共军控制区（哈尔滨）",
            "name_en": "CCP-held Harbin",
            "controller": {"qid": "Q17427", "zh": "中国共产党"},
            "from": "1946-04-28",
            "until": "1946-06-07",
            "geometry": {"roc_counties": [harbin]},
            "approx": True,
            "note": "滨江县域。1946-04-28 进入哈尔滨。哈尔滨在吉林的滨江，不在黑龙江多边形里，也不把吉林全省提前。1946-06-07 起并入松花江以北的东北沦陷区。大致。县域为治所泰森多边形近似。未核对《中華民國史事紀要》。",
            "dates_note": "1946-04-28 起，收到 1946-06-07。",
            "sources": ["http://www.chinadaily.com.cn/dfpd/hlj/2011-04/28/content_12413529.htm", "https://zenodo.org/records/5721459"],
        })
        print("added harbin cell")

    if not any(z["id"] == "sjw_ccp_central_soviet" for z in doc["zones"]):
        doc["zones"].append({
            "id": "sjw_ccp_central_soviet",
            "group": "ccp_base",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "中央苏区（中共根据地，大致范围）",
            "name_en": "Central Soviet Area",
            "controller": {"qid": "Q1135255", "zh": "中华苏维埃共和国"},
            "from": "1931-11-07",
            "until": "1934-10-17",
            "geometry": {"roc_counties": by_name(features, SOVIET)},
            "approx": True,
            "note": "大致。县域为治所泰森多边形近似。1934年9月记载里剩下的瑞金、会昌、雩都、兴国、宁都、石城、宁化、长汀八个县城，不是辖境，也不是县界。未核对《中華民國史事紀要》。",
            "dates_note": "1931-11-07 成立。1934-10-17 中央红军由雩都出发，这一天起不再画这八个县域。",
            "sources": [
                "https://zh.wikipedia.org/wiki/中华苏维埃共和国",
                "https://zh.wikipedia.org/wiki/长征",
                "https://zenodo.org/records/5721459",
            ],
        })
        print("added central soviet", len(SOVIET))

    EXTENTS.write_text(json.dumps(extents, ensure_ascii=False, indent=1), encoding="utf-8")
    ZONES.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("zones", len(doc["zones"]), "extents", len(extents))

    bei = json.loads(BEIYANG.read_text(encoding="utf-8"))
    before = len(bei["fronts"])
    bei["fronts"] = [f for f in bei["fronts"] if f.get("id") != "soviet-ring"]
    for war in bei["wars"]:
        if war.get("id") == "soviet-1931":
            war["note"] = (
                "中文维基百科《中华苏维埃共和国》记1931-11-07成立。《长征》记1934年9月下旬中央苏区只剩"
                "瑞金、会昌、雩都、兴国、宁都、石城、宁化、长汀一带，10月17日中央红军由雩都出发。"
                "这八个县城各用治所泰森多边形近似，大致范围，不是辖境，也不是县界。直边环线已撤。未核对《中華民國史事紀要》。"
            )
    BEIYANG.write_text(json.dumps(bei, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("fronts", before, "->", len(bei["fronts"]))


if __name__ == "__main__":
    main()
