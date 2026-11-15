#!/usr/bin/env python3
"""把争议区用到的 Natural Earth 轮廓收成一份小几何。

只取已经在 data/basemaps_raw 里的 1:10m 行政界（公有领域）。
这是现代行政轮廓，不是当日控制线。没有对应单元的地区不在这里编一块多边形。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa: E402

RAW = config.DATA_DIR / "basemaps_raw"
OUT = config.DATA_DIR / "curated" / "geom" / "status_areas.geojson"

# id -> ("admin1", [iso]) 或 ("admin0", [a3])
SPECS = {
    "crimea": ("admin1", ["UA-43", "UA-40"]),
    "donbas_oblasts": ("admin1", ["UA-14", "UA-09"]),
    "four_oblasts": ("admin1", ["UA-14", "UA-09", "UA-23", "UA-65"]),
    "abkhazia": ("admin1", ["GE-AB"]),
    "northern_cyprus": ("admin0", ["CYN"]),
    "kosovo": ("admin0", ["KOS"]),
    "western_sahara": ("admin0", ["SAH"]),
}


def features(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))["features"]


def main():
    a1 = features("ne_10m_admin_1_states_provinces.geojson")
    a0 = features("ne_10m_admin_0_countries.geojson")
    out = []
    for gid, (kind, codes) in SPECS.items():
        want = set(codes)
        if kind == "admin1":
            fs = [f for f in a1 if f["properties"].get("iso_3166_2") in want]
            got = {f["properties"]["iso_3166_2"] for f in fs}
        else:
            fs = [f for f in a0 if f["properties"].get("ADM0_A3") in want]
            got = {f["properties"]["ADM0_A3"] for f in fs}
        missing = want - got
        if missing:
            raise SystemExit(f"{gid} missing {missing}")
        g = make_valid(unary_union([make_valid(shape(f["geometry"])) for f in fs]))
        g = g.simplify(0.002, preserve_topology=True)
        if g.is_empty:
            raise SystemExit(f"{gid} empty")
        p = g.representative_point()
        out.append({
            "type": "Feature",
            "properties": {
                "id": gid,
                "source": "Natural Earth 1:10m",
                "license": "public domain",
                "codes": codes,
                "probe": [round(p.x, 4), round(p.y, 4)],
            },
            "geometry": mapping(g),
        })
        print(f"{gid:20} area={g.area:.3f} probe={p.x:.3f},{p.y:.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
