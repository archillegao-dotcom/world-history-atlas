"""把 ENP-China 的 CC0 民国省界收成轮廓。规则在 data/curated/roc_admin.json，本脚本只写几何。

五个年份档里同一 s_id 的几何相同，所以不生成两套线。
源压缩包不进仓库。解压到 /tmp/rocprov/ex 后再运行。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import shapefile
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "roc_admin_geom.json"
SRC = Path("/tmp/rocprov/ex")
R = 6378137.0
SKIP = {"19"}  # 蒙古。西藏留下几何，规则里不画。

LATE_NAMES = {"合江", "嫩江", "安東", "松江", "興安", "遼北", "遼寧", "吉林", "黑龍江", "台灣"}


def to_ll(x, y, z=None):
    lon = x / R * 180.0 / math.pi
    lat = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)
    return lon, lat


def geom_of(shp):
    g = make_valid(transform(to_ll, shape(shp.__geo_interface__)))
    g = g.simplify(0.03, preserve_topology=True)
    if g.geom_type == "GeometryCollection":
        g = max(g.geoms, key=lambda x: x.area)
    return g


def dump(g):
    return json.loads(json.dumps(mapping(g), ensure_ascii=False))


def main():
    base = shapefile.Reader(str(SRC / "Prov_1912_1921/1912_1921.shp"))
    rows = []
    for sr in base.iterShapeRecords():
        d = sr.record.as_dict()
        sid = d.get("s_id") or ""
        if not sid or sid in SKIP:
            continue
        g = geom_of(sr.shape)
        p = g.representative_point()
        rows.append({
            "sid": sid,
            "name_1912": d.get("p_12_21_nz") or "",
            "label": [round(p.x, 4), round(p.y, 4)],
            "geom": dump(g),
        })
    late = shapefile.Reader(str(SRC / "Prov_1947_1949/1947_1949.shp"))
    seen = set()
    for sr in late.iterShapeRecords():
        d = sr.record.as_dict()
        name = d.get("p_47_49_nz") or ""
        if name not in LATE_NAMES:
            continue
        sid = "1947-" + name
        if sid in seen:
            continue
        # 旧的吉林、奉天、黑龙江仍用 1912 档。1947 档里同名且 s_id 为空或新编号的才是东北九省。
        if d.get("s_id") and name not in ("遼寧",) and d.get("s_id") not in ("49", "999", ""):
            continue
        if name == "遼寧" and d.get("s_id") != "49":
            continue
        if name in ("吉林", "黑龍江") and d.get("s_id"):
            continue
        seen.add(sid)
        g = geom_of(sr.shape)
        p = g.representative_point()
        rows.append({
            "sid": sid,
            "name_1912": name,
            "label": [round(p.x, 4), round(p.y, 4)],
            "geom": dump(g),
        })
    OUT.write_text(json.dumps({"units": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, "units", len(rows), "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
