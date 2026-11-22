"""四川防区与西北马家的县域实控。县名对 MCGD 1931 年治所。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

_PACK = None


def _on(day: str, start: str | None, end: str | None) -> bool:
    if start and day < start:
        return False
    if end and not (day < end):
        return False
    return True


class _Index:
    def __init__(self, base: Path):
        raw = json.loads((base / "roc_garrison.json").read_text(encoding="utf-8"))
        seats = {}
        csv_path = base / "geom" / "MCGD_Rep_V2.csv"
        for row in csv.DictReader(csv_path.open(encoding="utf-8-sig")):
            seats.setdefault(row["Name_ZhT"], f"mcgd:{row['FID']}")
        self.periods = []
        for period in raw["periods"]:
            ids = []
            for name in period["counties"]:
                cid = seats.get(name)
                if not cid:
                    raise SystemExit(f"roc_garrison county not in MCGD: {name}")
                ids.append(cid)
            item = dict(period)
            item["ids"] = ids
            self.periods.append(item)
        self.by_id = {}
        for period in self.periods:
            for cid in period["ids"]:
                self.by_id.setdefault(cid, []).append(period)
        self.pending = raw["pending"]
        gj = json.loads((base / "geom" / "roc_county_cells.geojson").read_text(encoding="utf-8"))
        self.geoms = []
        self.meta = []
        for feat in gj["features"]:
            props = feat["properties"]
            cid = props["id"]
            if cid not in self.by_id and props.get("province") not in ("四川", "西康", "青海", "寧夏", "甘肅"):
                continue
            self.geoms.append(shape(feat["geometry"]))
            self.meta.append(props)
        self.tree = STRtree(self.geoms)

    def at(self, lon: float, lat: float, day: str, province_id: str | None) -> dict | None:
        point = Point(lon, lat)
        hits = list(self.tree.query(point, predicate="intersects"))
        if len(hits) == 0:
            return None
        pick = min(hits, key=lambda i: self.geoms[int(i)].area)
        props = self.meta[int(pick)]
        cid = props["id"]
        chosen = None
        for period in self.by_id.get(cid, []):
            if not _on(day, period["from"], period["until"]):
                continue
            if chosen is None or period["from"] > chosen["from"]:
                chosen = period
        if chosen:
            return {
                "id": cid,
                "name": props["name"],
                "actual": chosen["actual"],
                "confidence": chosen["confidence"],
                "from": chosen["from"],
                "until": chosen["until"],
                "note": chosen["note"],
                "sources": chosen["sources"],
            }
        for row in self.pending:
            if province_id not in row["provinces"]:
                continue
            if not _on(day, row["from"], row["until"]):
                continue
            return {
                "id": cid,
                "name": props["name"],
                "actual": "待考",
                "confidence": "待考",
                "from": row["from"],
                "until": row["until"],
                "note": row["note"],
                "sources": [],
            }
        return None


def index(data_dir) -> _Index:
    global _PACK
    base = Path(data_dir) / "curated"
    if _PACK is None or _PACK[0] != base:
        _PACK = (base, _Index(base))
    return _PACK[1]


def county_at(data_dir, lon, lat, day: str, province_id: str | None) -> dict | None:
    if lon is None or lat is None:
        return None
    return index(data_dir).at(float(lon), float(lat), day, province_id)


def zone_specs(data_dir) -> list[dict]:
    out = []
    for period in index(data_dir).periods:
        if period["actual"] in ("待考", "实控待考"):
            continue
        out.append({
            "id": f"garrison_{period['id']}",
            "group": "roc_garrison",
            "kind": "de_facto",
            "as_polity": False,
            "name_zh": period["actual"],
            "name_en": "County garrison",
            "controller": {"qid": f"rocact:{period['id']}", "zh": period["actual"]},
            "from": period["from"],
            "until": period["until"],
            "geometry": {"roc_counties": period["ids"], "nosimplify": True},
            "approx": True,
            "dates_note": f"{period['from']} 起至 {period['until']}。{period['confidence']}。",
            "note": period["note"] + "县域为1931年治所泰森多边形近似，不是县界。名义所属仍按省界。",
            "sources": period["sources"],
        })
    return out
