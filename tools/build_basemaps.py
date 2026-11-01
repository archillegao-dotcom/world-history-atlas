#!/usr/bin/env python3
"""
预处理 historical-basemaps (aourednik, GPL-3.0) 的 GeoJSON 快照：
- 几何简化(约 0.02°)以减小体积，保留拓扑大致形状；
- 每个要素加稳定 id (fid)，便于前端点击后回传；
- 输出 data/basemaps/<year>.geojson.gz 与 data/basemaps/index.json（年份列表，负数=公元前）。
来源 / Source: https://github.com/aourednik/historical-basemaps
另外：Natural Earth 1:50m admin-0 国家边界（公有领域，https://www.naturalearthdata.com/ ，
文件 ne_50m_admin_0_countries.geojson）作为「现代」快照，年份记为 2011，用于 2011 年至今。
用法: python tools/build_basemaps.py [--src 原始geojson目录] [--tol 0.02]
"""
import argparse, gzip, json, os, re
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WHA_DATA_DIR", ROOT / "data"))
BASE_URL = "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/"


def year_of(fname: str):
    m = re.match(r"world_(bc)?(\d+)\.geojson$", fname)
    if not m:
        return None
    y = int(m.group(2))
    return -y if m.group(1) else y


def round_coords(geom, nd=3):
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], nd), round(c[1], nd)]
        return [r(x) for x in c]
    geom["coordinates"] = r(geom["coordinates"])
    return geom


NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
MODERN_YEAR = 2011


def ne_props(p):
    """Natural Earth 属性 -> 与 historical-basemaps 相同的字段（并保留中文名与 Wikidata QID）。"""
    return {"NAME": p.get("NAME"), "ABBREVN": p.get("ABBREV"), "SUBJECTO": p.get("SOVEREIGNT"),
            "PARTOF": p.get("ADMIN"), "BORDERPRECISION": 3, "NAME_ZH": p.get("NAME_ZH"), "QID": p.get("WIKIDATAID")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DATA / "basemaps_raw"))
    ap.add_argument("--tol", type=float, default=0.02)
    a = ap.parse_args()
    out = DATA / "basemaps"
    out.mkdir(parents=True, exist_ok=True)
    index = []
    files = sorted(Path(a.src).glob("world_*.geojson"))
    ne = Path(a.src) / "ne_50m_admin_0_countries.geojson"
    if ne.exists():
        files.append(ne)
    for f in files:
        y = MODERN_YEAR if f == ne else year_of(f.name)
        if y is None:
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        feats = []
        for i, ft in enumerate(d["features"]):
            if not ft.get("geometry"):
                continue
            g = shape(ft["geometry"])
            if not g.is_valid:
                g = make_valid(g)
            g = g.simplify(a.tol, preserve_topology=True)
            if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
                # make_valid 可能产生 GeometryCollection，只保留面
                polys = [p for p in getattr(g, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")]
                if not polys:
                    continue
                from shapely.ops import unary_union
                g = unary_union(polys)
            p = ft.get("properties") or {}
            props = ne_props(p) if f == ne else {"NAME": p.get("NAME"), "ABBREVN": p.get("ABBREVN"),
                                                 "SUBJECTO": p.get("SUBJECTO"), "PARTOF": p.get("PARTOF"),
                                                 "BORDERPRECISION": p.get("BORDERPRECISION")}
            feats.append({"type": "Feature", "id": i, "properties": {"fid": i, **props},
                          "geometry": round_coords(mapping(g))})
        src = NE_URL if f == ne else BASE_URL + f.name
        fc = {"type": "FeatureCollection", "year": y, "source": src, "features": feats}
        (out / f"{y}.geojson.gz").write_bytes(gzip.compress(json.dumps(fc, ensure_ascii=False, separators=(",", ":")).encode()))
        index.append({"year": y, "file": f"{y}.geojson.gz", "features": len(feats), "source": src,
                      "label": "现代边界（Natural Earth 5.x，约 2020 年代）" if f == ne else "historical-basemaps"})
        print(y, len(feats))
    index.sort(key=lambda x: x["year"])
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
