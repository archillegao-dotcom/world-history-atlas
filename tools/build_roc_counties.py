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
    ("桂林", 110.29, 25.27, "1944-11-10"),
    ("杭州", 120.169, 30.294, "1937-12-24"),
    ("苏州", 120.614, 31.318, "1937-11-19"),
    ("青岛", 120.038, 36.274, "1938-01-10"),
    ("厦门", 118.077, 24.460, "1938-05-13"),
    ("无锡", 120.291, 31.583, "1937-11-25"),
    ("常州", 119.943, 31.765, "1937-11-29"),
    ("芜湖", 118.370, 31.342, "1937-12-10"),
    ("济南", 116.998, 36.690, "1937-12-27"),
    ("开封", 114.345, 34.802, "1938-06-06"),
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
    doc["zones"].extend(supplements)

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
