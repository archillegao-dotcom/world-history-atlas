"""欧洲历史一级行政区。

几何、年份和许可在 data/curated/geom/europe_admin.geojson。
点落在多块里时取面积最小的一块。没有几何的地方不补今天的省界。
"""
from __future__ import annotations

import json

from shapely.geometry import Point, shape

_CACHE: dict | None = None


def _on(day: str, start: str | None, end: str | None) -> bool:
    if start and day < start:
        return False
    if end and not (day < end):
        return False
    return True


def dataset(data_dir) -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = data_dir / "curated" / "geom" / "europe_admin.geojson"
    if not path.exists():
        _CACHE = {"units": [], "gaps": [], "note": ""}
        return _CACHE
    data = json.loads(path.read_text(encoding="utf-8"))
    units = []
    for feat in data.get("features") or []:
        prop = dict(feat.get("properties") or {})
        geom = feat.get("geometry")
        if not geom:
            continue
        prop["geom"] = geom
        prop["_shape"] = shape(geom)
        units.append(prop)
    _CACHE = {"units": units, "gaps": data.get("gaps") or [], "note": data.get("note") or ""}
    return _CACHE


def features_for(units, day: str) -> list[dict]:
    out = []
    for unit in units:
        if not _on(day, unit.get("from"), unit.get("until")):
            continue
        point = unit["_shape"].representative_point()
        out.append({
            "id": unit["id"],
            "name": unit.get("name"),
            "kind": unit.get("kind") or "",
            "nominal": unit.get("nominal") or "",
            "label": [point.x, point.y],
            "geom": unit["geom"],
        })
    return out


def place_at(pack, lon: float | None, lat: float | None, day: str) -> dict:
    empty = {
        "status": "none", "name": None, "name_src": None, "kind": "", "nominal": None, "actual": None,
        "scheme": "", "line_note": "", "sources": [], "license": None, "europe": False,
        "note": "省界待考。这里没有可再分发的当年省界，不画今天的省界。",
    }
    if lon is None or lat is None:
        return empty
    point = Point(lon, lat)
    hits = [
        unit for unit in pack["units"]
        if _on(day, unit.get("from"), unit.get("until")) and unit["_shape"].covers(point)
    ]
    if not hits:
        return empty
    hits.sort(key=lambda unit: (unit["_shape"].area, unit.get("from") or ""))
    unit = hits[0]
    precision = unit.get("precision") or ""
    return {
        "status": "draw",
        "id": unit["id"],
        "name": unit.get("name"),
        "name_src": unit.get("name_src"),
        "kind": unit.get("kind") or "",
        "nominal": unit.get("nominal") or "—",
        "actual": "不是实控记录",
        "scheme": "",
        "line_note": "",
        "sources": [unit["url"]] if unit.get("url") else [],
        "license": unit.get("license"),
        "europe": True,
        "note": precision + "不画今天的省界。",
    }


def coverage_note(pack: dict) -> str:
    gaps = "".join(pack.get("gaps") or [])
    return (pack.get("note") or "") + gaps + "没有这些几何的国家和年份标省界待考，不画今天的省界。"
