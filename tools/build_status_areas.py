#!/usr/bin/env python3
"""把争议区用到的 Natural Earth 轮廓收成一份小几何。

只取已经在 data/basemaps_raw 里的 1:10m 行政界（公有领域）。
这是现代行政轮廓，不是当日控制线。没有对应单元的地区不在这里编一块多边形。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa: E402

RAW = config.DATA_DIR / "basemaps_raw"
OUT = config.DATA_DIR / "curated" / "geom" / "status_areas.geojson"

# id -> ("admin1", [iso]) 或 ("admin0", [a3])
# 这些是现代行政轮廓，调用处必须自己写明不能回贴到哪一年。
SPECS = {
    "crimea": ("admin1", ["UA-43", "UA-40"]),
    "donbas_oblasts": ("admin1", ["UA-14", "UA-09"]),
    "four_oblasts": ("admin1", ["UA-14", "UA-09", "UA-23", "UA-65"]),
    "abkhazia": ("admin1", ["GE-AB"]),
    "northern_cyprus": ("admin0", ["CYN"]),
    "kosovo": ("admin0", ["KOS"]),
    "western_sahara": ("admin0", ["SAH"]),
    # 查谟-克什米尔与拉达克合在一起，是今天的印度管治范围。锡亚琴在 KAS，阿克赛钦在新疆，都不在这里。
    "kashmir_india": ("admin1", ["IN-JK", "IN-LA"]),
    "kashmir_pakistan": ("admin1", ["PK-JK", "PK-GB"]),
    "siachen": ("admin0", ["KAS"]),
    "west_bank": ("admin1", ["PS-WBK"]),
    "gaza": ("admin1", ["PS-GZZ"]),
    # 含台湾本岛、澎湖、金门。马祖纬度超出这块国家轮廓，不在这里。
    "taiwan": ("admin0", ["TWN"]),
    "falklands": ("admin0", ["FLK"]),
    "paracel": ("admin1", ["CN-X01~"]),
    "spratly": ("admin0", ["PGA"]),
    # 今下莱茵、上莱茵、摩泽尔。贝尔福不在上莱茵省。孚日省被割的两个县不在这里。
    "alsace_lorraine": ("admin1", ["FR-67", "FR-68", "FR-57"]),
}


def _parts(geom):
    g = make_valid(geom)
    return list(g.geoms) if g.geom_type.startswith("Multi") else [g]


def matsu():
    """马祖。Natural Earth 国家多边形里没有这些小岛，取 1:10m 微型岛里落在连江县范围内的碎块。

    范围与已有控制区相同：东经 119.85–120.55、北纬 25.9–26.42，单块面积不超过 0.02。
    这是现代岸线，不是 1949 年的测绘。
    """
    bb = box(119.85, 25.9, 120.55, 26.42)
    parts = []
    for f in features("ne_10m_minor_islands.geojson"):
        for p in _parts(shape(f["geometry"])):
            if p.area <= 0.02 and bb.contains(p.representative_point()):
                parts.append(p)
    if len(parts) < 4:
        raise SystemExit(f"matsu too few parts: {len(parts)}")
    return make_valid(unary_union(parts))


def south_georgia():
    """南乔治亚。SGS 这一国同时含南桑威奇。

    南乔治亚碎块的代表点在西经 35° 以西，南桑威奇在西经 28° 附近，中间没有碎块。
    西经 32° 只用来分开这些现成碎块，不是勘界。
    """
    fs = [f for f in features("ne_10m_admin_0_countries.geojson") if f["properties"].get("ADM0_A3") == "SGS"]
    if len(fs) != 1:
        raise SystemExit(f"SGS count {len(fs)}")
    parts = [p for p in _parts(shape(fs[0]["geometry"])) if p.representative_point().x < -32]
    if not parts:
        raise SystemExit("south_georgia empty")
    return make_valid(unary_union(parts)).simplify(0.002, preserve_topology=True)


def habomai_shikotan():
    """齿舞、色丹。已有千岛岸线里，代表点在北纬 43.95° 以南的碎块。

    色丹代表点约 43.80°，国后约 44.10°，中间没有碎块。
    43.95° 只用来分开这些现成碎块，不是勘界。不含国后、择捉。
    """
    p = config.DATA_DIR / "curated" / "geom" / "kuril_islands.geojson"
    gj = json.loads(p.read_text(encoding="utf-8"))
    parts = [part for part in _parts(shape(gj["geometry"])) if part.representative_point().y < 43.95]
    if len(parts) < 4:
        raise SystemExit(f"habomai_shikotan too few parts: {len(parts)}")
    return make_valid(unary_union(parts)).simplify(0.0005, preserve_topology=True)


def kuril_south():
    """已有千岛岸线里，代表点在北纬 45.4° 以南的碎块。

    择捉代表点约 44.98°，得抚约 45.9°，中间没有碎块。
    45.4° 只用来分开这些现成碎块，不是勘界，也不是整条千岛。
    """
    p = config.DATA_DIR / "curated" / "geom" / "kuril_islands.geojson"
    gj = json.loads(p.read_text(encoding="utf-8"))
    g = make_valid(shape(gj["geometry"]))
    parts = [part for part in g.geoms if part.representative_point().y < 45.4]
    if len(parts) < 4:
        raise SystemExit(f"kuril_south too few parts: {len(parts)}")
    out = make_valid(unary_union(parts)).simplify(0.002, preserve_topology=True)
    return out


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
        # 小岛用更小的简化距离，否则岛岸会离开可以点中的坐标。
        tol = 0.0001 if g.area < 0.02 else 0.002
        g = g.simplify(tol, preserve_topology=True)
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
    g = kuril_south()
    p = g.representative_point()
    out.append({
        "type": "Feature",
        "properties": {
            "id": "kuril_south",
            "source": "Natural Earth 1:10m shoreline, southern fragments of curated/geom/kuril_islands.geojson",
            "license": "public domain",
            "codes": ["lat<45.4"],
            "probe": [round(p.x, 4), round(p.y, 4)],
        },
        "geometry": mapping(g),
    })
    print(f"{'kuril_south':20} area={g.area:.3f} probe={p.x:.3f},{p.y:.3f}")
    for gid, geom, note in (
        ("matsu", matsu(), "Natural Earth 1:10m minor islands in the Matsu bbox"),
        ("south_georgia", south_georgia(), "Natural Earth 1:10m SGS fragments west of 32W"),
        ("habomai_shikotan", habomai_shikotan(), "Natural Earth 1:10m Kuril fragments south of 43.95N"),
    ):
        rp = geom.representative_point()
        out.append({
            "type": "Feature",
            "properties": {
                "id": gid,
                "source": note,
                "license": "public domain",
                "probe": [round(rp.x, 4), round(rp.y, 4)],
            },
            "geometry": mapping(geom),
        })
        print(f"{gid:20} area={geom.area:.3f} probe={rp.x:.3f},{rp.y:.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
