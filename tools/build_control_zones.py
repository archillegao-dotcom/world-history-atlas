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
    if not gs:
        raise SystemExit(f"empty geometry: {spec}")
    g = make_valid(unary_union(gs))
    if "intersect_bbox" in spec:
        g = make_valid(g.intersection(box(*spec["intersect_bbox"])))
    if "intersect" in spec:
        g = make_valid(g.intersection(resolve(spec["intersect"])))
    if "minus" in spec:
        g = make_valid(g.difference(resolve(spec["minus"])))
    for u in spec.get("union", []):   # 再并上其他几何规格（如金朝 = 宋朝淮河以北 ∪ 辽朝故地）
        g = make_valid(unary_union([g, resolve(u)]))
    return g.simplify(0.002, preserve_topology=True)


def main():
    cur = json.loads((config.DATA_DIR / "curated" / "control_zones.json").read_text(encoding="utf-8"))
    out = []
    for z in cur["zones"]:
        g = resolve(z["geometry"])
        if g.is_empty or g.area < 1e-6:
            print(f"{z['id']:32} EMPTY geometry, skipped")
            continue
        rec = {k: v for k, v in z.items() if k != "geometry"}
        rec["geom"] = mapping(g)
        rec["bbox"] = [round(x, 4) for x in g.bounds]
        out.append(rec)
        print(f"{z['id']:32} parts={len(parts(g)):3} area={g.area:8.3f} bbox={rec['bbox']}")
    with gzip.open(config.DATA_DIR / "control_zones.json.gz", "wt", encoding="utf-8") as fh:
        json.dump({"zones": out}, fh, ensure_ascii=False, separators=(",", ":"))
    print("zones:", len(out))


if __name__ == "__main__":
    main()
