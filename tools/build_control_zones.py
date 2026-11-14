#!/usr/bin/env python3
"""
实际控制区（data/curated/control_zones.json）→ 几何解析 → data/control_zones.json.gz
几何规格见 control_zones.json 的 _doc。需要 data/basemaps_raw/ 下的 Natural Earth 1:10m 文件：
  ne_10m_admin_0_countries.geojson、ne_10m_admin_1_states_provinces.geojson
  （https://github.com/nvkelso/natural-earth-vector/tree/master/geojson，公有领域）
用法：.venv/bin/python tools/build_control_zones.py
"""
from __future__ import annotations

import gzip
import json
import lzma
import sys
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa: E402

RAW = config.DATA_DIR / "basemaps_raw"   # 另需 ne_10m_minor_islands.geojson
_cache = {}


def ne(name):
    if name not in _cache:
        _cache[name] = json.loads((RAW / name).read_text(encoding="utf-8"))["features"]
    return _cache[name]


def parts(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def roc_shapes():
    """ENP-China 历史省界，与虚线图层同一份几何。按省 id 取，不再做第二遍简化。"""
    if "roc" not in _cache:
        rules = json.loads((config.DATA_DIR / "curated" / "roc_admin.json").read_text(encoding="utf-8"))
        geoms = json.loads((config.DATA_DIR / "curated" / "roc_admin_geom.json").read_text(encoding="utf-8"))
        by_sid = {u["sid"]: make_valid(shape(u["geom"])) for u in geoms["units"]}
        _cache["roc"] = {u["id"]: by_sid[u["sid"]] for u in rules["units"] if u["sid"] in by_sid}
    return _cache["roc"]


# 这两条如果整省另画，会盖住已经核对过的首都点：1920 年北京的五色旗、1935 年南京的青天白日满地红。
SKIP_FILL = {"南京国民政府", "皖系"}
CCP_ACTUAL = "中国共产党"
PRC_FROM, PRC_UNTIL = "1949-10-01", "1950-01-01"
# 台湾另有底图多边形。西藏不拿这套行省轮廓覆盖甘丹颇章。
PRC_EXCLUDE = {"taiwan", "tibet"}
ENP_URL = "https://www.virtualshanghai.net/Data/Tables?ID=198"
SLUG = {
    "晋系（阎锡山）": "jin",
    "滇系（唐继尧）": "dian-tang",
    "滇系（龙云）": "dian-long",
    "旧桂系（陆荣廷）": "gui-old",
    "桂系（李宗仁、白崇禧）": "gui",
    "旧桂系驻粤": "gui-gd",
    "国民政府（驻广州）": "gz-gov",
    "盛世才": "sheng",
    "川军（刘湘）": "liu-xiang",
    "刘文辉": "liu-wenhui",
    "奉系（张作霖）": "feng-zhang",
    "奉系（张学良）": "feng-xue",
    "奉系": "feng",
    "东北军（张学良）": "dongbei",
    "西北马家（马鸿逵）": "ma-hongkui",
    "西北马家": "ma-qinghai",
    "韩复榘": "han",
    "陈济棠": "chen",
}


def _draw_spans(unit):
    if "draw" in unit:
        return [(d["from"], d["until"]) for d in unit["draw"]]
    return [("1912-01-01", "1950-01-01")]


def _pieces(rules):
    """(actual, start, end, unit id) ，已经和该省的绘制区间求过交。"""
    out = []
    for unit in rules["units"]:
        for control in unit.get("controls") or []:
            actual = control.get("actual")
            if not actual or actual in SKIP_FILL:
                continue
            for a0, b0 in _draw_spans(unit):
                a, b = max(control["from"], a0), min(control["until"], b0)
                if a < b:
                    out.append((actual, a, b, unit["id"]))
    return out


def _slices(pieces):
    """同一实控方、同一组省、连续的日期并成一段。"""
    by_actual = {}
    for actual, a, b, uid in pieces:
        by_actual.setdefault(actual, []).append((a, b, uid))
    merged = []
    for actual, rows in by_actual.items():
        dates = sorted({a for a, _, _ in rows} | {b for _, b, _ in rows})
        for a, b in zip(dates, dates[1:]):
            ids = tuple(sorted({uid for s, e, uid in rows if s <= a and b <= e}))
            if not ids:
                continue
            if merged and merged[-1][0] == actual and merged[-1][3] == ids and merged[-1][2] == a:
                prev = merged[-1]
                merged[-1] = (actual, prev[1], b, ids)
            else:
                merged.append((actual, a, b, ids))
    return merged


def province_fill_zones():
    """按省界面板的实控记录，用历史省界整省填色。

    军阀填色放在策展多边形之前，后来的占领层和守住区会把城池切走。
    1949-10-01 起共军控制改记中华人民共和国，不再另挂一块。这一天之前的共军填色放在最后，盖住底图。
    """
    rules = json.loads((config.DATA_DIR / "curated" / "roc_admin.json").read_text(encoding="utf-8"))
    names = {u["id"]: u.get("name") or u["id"] for u in rules["units"]}
    early, late = [], []
    for actual, a, b, ids in _slices(_pieces(rules)):
        if actual == CCP_ACTUAL:
            if a >= PRC_FROM:
                continue
            b = min(b, PRC_FROM)
            if a >= b:
                continue
            bucket = late
            qid, zh, name_zh = "Q17427", "中国共产党", "共军控制区"
            slug = "ccp"
        else:
            bucket = early
            slug = SLUG.get(actual, "x")
            qid, zh, name_zh = f"rocact:{slug}", actual, actual
        listed = "、".join(names.get(i, i) for i in ids)
        bucket.append({
            "id": f"rocfill_{slug}_{a}",
            "group": "chinese_civil_war" if actual == CCP_ACTUAL else "roc_warlord",
            "kind": "occupied" if actual == CCP_ACTUAL else "de_facto",
            "as_polity": True,
            "name_zh": name_zh,
            "name_en": "Historical-province control",
            "controller": {"qid": qid, "zh": zh},
            "from": a,
            "until": b,
            "geometry": {"roc_ids": list(ids), "nosimplify": True},
            "approx": True,
            "dates_note": f"{a} 起至 {b}。省份：{listed}。按省会或通电日整省填色，不是逐县。",
            "note": "边界用 ENP-China 历史省界，和虚线是同一套。省内不是逐县。前线、点和线的占领区仍是大致范围。未核对《中華民國史事紀要》。",
            "sources": [ENP_URL],
        })
    prc_ids = []
    for unit in rules["units"]:
        if unit["id"] in PRC_EXCLUDE:
            continue
        if any(max(s, PRC_FROM) < min(e, PRC_UNTIL) for s, e in _draw_spans(unit)):
            prc_ids.append(unit["id"])
    prc_ids.sort()
    early.append({
        "id": "rocfill_prc_1949-10-01",
        "group": "chinese_civil_war",
        "kind": "de_facto",
        "as_polity": True,
        "name_zh": "中华人民共和国",
        "name_en": "People's Republic of China",
        "controller": {"qid": "Q148", "zh": "中华人民共和国"},
        "from": PRC_FROM,
        "until": PRC_UNTIL,
        "geometry": {"roc_ids": prc_ids, "nosimplify": True},
        "approx": True,
        "dates_note": "1949-10-01 起用历史省界。广东、广西和西南的守住区仍按原日期从这块里切出。台湾、西藏不在这块里。",
        "note": "边界用 ENP-China 历史省界，和虚线是同一套。不是逐县。未核对《中華民國史事紀要》。",
        "sources": [ENP_URL],
    })
    return early, late


def resolve(spec):
    gs = []
    if "admin1" in spec:
        want = set(spec["admin1"])
        fs = [f for f in ne("ne_10m_admin_1_states_provinces.geojson") if f["properties"].get("iso_3166_2") in want]
        missing = want - {f["properties"]["iso_3166_2"] for f in fs}
        if missing:
            raise SystemExit(f"admin1 not found: {missing}")
        gs += [make_valid(shape(f["geometry"])) for f in fs]
    if "admin0_parts" in spec:
        a = spec["admin0_parts"]
        bb = box(*a["bbox"])
        for f in ne("ne_10m_admin_0_countries.geojson"):
            if f["properties"].get("ADM0_A3") in a["a3"]:
                for p in parts(make_valid(shape(f["geometry"]))):
                    if p.area <= a.get("max_area", 1e9) and bb.contains(p.representative_point()):
                        gs.append(p)
        # Natural Earth 1:10m 国家多边形不含很小的岛：同时取 ne_10m_minor_islands 中落在 bbox 内的岛
        for f in ne("ne_10m_minor_islands.geojson"):
            for p in parts(make_valid(shape(f["geometry"]))):
                if bb.contains(p.representative_point()):
                    gs.append(p)
    if "basemap" in spec:
        from backend.geo import BasemapStore
        B = BasemapStore()
        b = spec["basemap"]
        gs += [f["geom"] for f in B.features(b["snap"]).values() if f["props"].get("NAME") == b["name"]]
    if "cshapes" in spec:   # CShapes 2.0 在某日期有效的行（按 gwcode）
        c = spec["cshapes"]
        if "cs" not in _cache:
            from backend.datafile import read_json
            _cache["cs"] = read_json(config.DATA_DIR / "cshapes.json.gz")
        k = int(c["date"].replace("-", ""))
        for r in _cache["cs"]["rows"]:
            if r["gw"] in c["gw"] and r["from"] <= k and (r["to"] is None or k < r["to"]):
                gs.append(make_valid(shape(r["geom"])))
    if "polygon" in spec:
        gs.append(make_valid(shape({"type": "Polygon", "coordinates": [spec["polygon"]]})))
    if "geojson" in spec:
        gj = json.loads((config.DATA_DIR / spec["geojson"]).read_text(encoding="utf-8"))
        geom = gj["geometry"] if isinstance(gj, dict) and gj.get("type") == "Feature" else gj
        gs.append(make_valid(shape(geom)))
    if "roc_ids" in spec:
        table = roc_shapes()
        missing = [i for i in spec["roc_ids"] if i not in table]
        if missing:
            raise SystemExit(f"roc_ids not found: {missing}")
        gs += [table[i] for i in spec["roc_ids"]]
    if not gs:
        raise SystemExit(f"empty geometry: {spec}")
    if spec.get("nosimplify") and len(gs) == 1:
        g = make_valid(gs[0])
    else:
        g = make_valid(unary_union(gs))
    if "intersect_bbox" in spec:
        g = make_valid(g.intersection(box(*spec["intersect_bbox"])))
    if "intersect" in spec:
        g = make_valid(g.intersection(resolve(spec["intersect"])))
    if "minus" in spec:
        g = make_valid(g.difference(resolve(spec["minus"])))
    for u in spec.get("union", []):   # 再并上其他几何规格（如金朝 = 宋朝淮河以北 ∪ 辽朝故地）
        g = make_valid(unary_union([g, resolve(u)]))
    if spec.get("nosimplify"):
        return g
    return g.simplify(0.002, preserve_topology=True)


def main():
    cur = json.loads((config.DATA_DIR / "curated" / "control_zones.json").read_text(encoding="utf-8"))
    early, late = province_fill_zones()
    # 1949 年那五块用的是今天的省界。改由上面的历史省界填色，不再叠在一起。
    zones = early + [z for z in cur["zones"] if not str(z.get("id", "")).startswith("ccw_ccp_1949_")] + late
    out = []
    for z in zones:
        g = resolve(z["geometry"])
        if g.is_empty or g.area < 1e-6:
            print(f"{z['id']:32} EMPTY geometry, skipped")
            continue
        rec = {k: v for k, v in z.items() if k != "geometry"}
        rec["geom"] = mapping(g)
        rec["bbox"] = [round(x, 4) for x in g.bounds]
        out.append(rec)
        print(f"{z['id']:32} parts={len(parts(g)):3} area={g.area:8.3f} bbox={rec['bbox']}")
    payload = json.dumps({"zones": out}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # 运行时优先读同名 .xz。只写 .gz 时，地图仍用旧的 .xz。
    with gzip.open(config.DATA_DIR / "control_zones.json.gz", "wb") as fh:
        fh.write(payload)
    with lzma.open(config.DATA_DIR / "control_zones.json.xz", "wb", preset=9) as fh:
        fh.write(payload)
    print("zones:", len(out))


if __name__ == "__main__":
    main()
