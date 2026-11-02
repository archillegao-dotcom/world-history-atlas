#!/usr/bin/env python3
"""
二战欧洲按月边界（Stanford Spatial History Lab「Building the New Order: 1938-1945」，Michael De Groot 2010）
→ data/ww2_europe.json.gz

原始数据：data/ww2_raw/EuropeanBorders_WWII.zip（https://web.stanford.edu/group/spatialhistory/Publications/HolocaustGeographies/EuropeanBorders_WWII.zip）
88 个月末快照（1938-02-28 – 1945-05-31），Europe Albers 投影（ED50），比例约 1:10,000,000。
数据只记录吞并/新设政治实体（不记录纯军事占领线）；各要素带 Foreign_Po（外交/占领状态）、Head_of_St、Govt_in_Ex 属性。
许可：作者「鼓励学术复用与改编，禁止商业使用」——本应用为免费非商业软件，注明出处使用。
输出：{"source", "months": [{"date": YYYYMMDD, "feats": [[name, status, head, exile, gid], ...]}], "geoms": {gid: geojson}}
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import shapefile
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "ww2_raw" / "EuropeanBorders_WWII"
MON = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
PRJ = open(next(iter(glob.glob(str(RAW / "December_31_1942.prj"))))).read()


def rnd(o, nd=3):
    if isinstance(o, (list, tuple)):
        return [rnd(x, nd) for x in o]
    return round(o, nd) if isinstance(o, float) else o


def main():
    tr = Transformer.from_crs(PRJ, "EPSG:4326", always_xy=True)
    months, geoms = [], {}
    files = []
    for f in glob.glob(str(RAW / "*_19*.shp")):
        m = re.match(r"(\w+?)_(\d+)_(\d{4})\.shp", Path(f).name)
        files.append((dt.date(int(m.group(3)), MON[m.group(1)], int(m.group(2))), f))
    for d, f in sorted(files):
        r = shapefile.Reader(f, encoding="latin-1")
        feats = []
        for sr in r.iterShapeRecords():
            rec = sr.record
            g = make_valid(transform(tr.transform, shape(sr.shape.__geo_interface__)))
            g = make_valid(g.simplify(0.01, preserve_topology=True))
            if g.geom_type == "GeometryCollection":
                from shapely.geometry import MultiPolygon
                ps = [q for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") for q in getattr(p, "geoms", [p])]
                g = MultiPolygon(ps)
            if g.is_empty:
                continue
            gj = {"type": g.geom_type, "coordinates": rnd(mapping(g)["coordinates"])}
            gid = hashlib.md5(json.dumps(gj).encode()).hexdigest()[:10]
            geoms[gid] = gj
            clean = lambda s: (s or "").replace("\x9a", "š").replace("\x8a", "Š").strip() if (s or "").strip() not in ("<Null>",) else ""
            feats.append([rec[0].strip(), clean(rec[1]), clean(rec[2]), clean(rec[3]), gid])
        months.append({"date": d.year * 10000 + d.month * 100 + d.day, "feats": feats})
        print(d, len(feats), len(geoms), flush=True)
    out = {"source": {"name": "Building the New Order: 1938-1945 (Stanford Spatial History Lab, Michael De Groot 2010)",
                      "url": "https://web.stanford.edu/group/spatialhistory/static/publications/pub51.html",
                      "data": "https://web.stanford.edu/group/spatialhistory/Publications/HolocaustGeographies/EuropeanBorders_WWII.zip",
                      "license": "作者声明：鼓励学术复用与改编，禁止商业使用（本应用免费、非商业，注明出处）",
                      "note": "只记录吞并与新设政治实体，不含军事前线；军事占领线由 data/curated/ww2_fronts.json 另行叠加"},
           "months": months, "geoms": geoms}
    p = ROOT / "data" / "ww2_europe.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("written", p.stat().st_size, "unique geoms", len(geoms))


if __name__ == "__main__":
    main()
