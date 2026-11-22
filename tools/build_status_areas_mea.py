#!/usr/bin/env python3
"""中东、非洲、南亚争议区的 Natural Earth 轮廓。

只收 data/basemaps_raw 里已有的 1:10m 行政界（公有领域）。
这是现代行政轮廓，用来表示有记载、且与这些单元大致相符的范围。
不是当日控制线。没有对应单元的地区不在这里编多边形。
输出 data/curated/geom/status_areas_mea.geojson，不改 status_areas.geojson。
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
OUT = config.DATA_DIR / "curated" / "geom" / "status_areas_mea.geojson"

# id -> ("admin1", [iso]) 或 ("admin0", [a3])
SPECS = {
    "somaliland": ("admin0", ["SOL"]),
    "eritrea": ("admin0", ["ERI"]),
    "south_sudan": ("admin0", ["SDS"]),
    "timor_leste": ("admin0", ["TLS"]),
    "libya": ("admin0", ["LBY"]),
    "yemen": ("admin0", ["YEM"]),
    "katanga": ("admin1", ["CD-KA"]),
    "krg_core": ("admin1", ["IQ-DA", "IQ-AR", "IQ-SU"]),
    # 原民主也门一侧。达利阿省（YE-DA）1998 年才设、横跨旧界，不收。
    "yemen_south": ("admin1", ["YE-AD", "YE-LA", "YE-AB", "YE-SH", "YE-HD", "YE-MR"]),
    # 原阿拉伯也门共和国一侧，同样不含达利阿。
    "yemen_north": ("admin1", [
        "YE-SD", "YE-HJ", "YE-JA", "YE-HU", "YE-TA", "YE-MA", "YE-SN",
        "YE-RA", "YE-BA", "YE-AM", "YE-IB", "YE-MW", "YE-DH", "YE-SA",
    ]),
}


def features(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))["features"]


def main():
    a1 = features("ne_10m_admin_1_states_provinces.geojson")
    a0 = features("ne_10m_admin_0_countries.geojson")
    yem = sorted({f["properties"].get("iso_3166_2") for f in a1 if f["properties"].get("adm0_a3") == "YEM"})
    used = set(SPECS["yemen_south"][1] + SPECS["yemen_north"][1] + ["YE-DA"])
    leftover = [c for c in yem if c not in used]
    if leftover:
        raise SystemExit(f"Yemen admin1 not assigned (except YE-DA): {leftover}")
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
                "note": "现代行政轮廓，大致，不是当日控制线",
            },
            "geometry": mapping(g),
        })
        print(f"{gid:20} area={g.area:.3f} probe={p.x:.3f},{p.y:.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
