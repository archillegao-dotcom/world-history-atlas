"""现代一级行政区参考线。

地图和 /api/admin1_ref 不再返回这些线。今天的省界不拿来代替历史省界。
只用仓库里已有的 Natural Earth 1:10m admin-1（公有领域）。
第一次请求只解析文件并记下每个多边形的外包范围；真正画线时只简化当前视野里的那一部分。
这些线是现代一级行政区参考线，不是古代或战时省界。没有历史省界数据时不补线。
"""
from __future__ import annotations

import json
import threading

from shapely.geometry import mapping, shape
from shapely.validation import make_valid

from . import config

_lock = threading.Lock()
_rows: list | None = None


def _bbox(coords) -> tuple[float, float, float, float] | None:
    minx = miny = 1e9
    maxx = maxy = -1e9

    def walk(node):
        nonlocal minx, miny, maxx, maxy
        if not node:
            return
        if isinstance(node[0], (int, float)):
            x, y = node[0], node[1]
            if x < minx:
                minx = x
            if y < miny:
                miny = y
            if x > maxx:
                maxx = x
            if y > maxy:
                maxy = y
            return
        for part in node:
            walk(part)

    walk(coords)
    if minx > maxx:
        return None
    return minx, miny, maxx, maxy


def _load() -> list:
    global _rows
    if _rows is not None:
        return _rows
    with _lock:
        if _rows is not None:
            return _rows
        path = config.DATA_DIR / "basemaps_raw" / "ne_10m_admin_1_states_provinces.geojson"
        if not path.exists():
            _rows = []
            return _rows
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for ft in data.get("features") or []:
            geom = ft.get("geometry") or {}
            box = _bbox(geom.get("coordinates"))
            if not box:
                continue
            props = ft.get("properties") or {}
            minx, miny, maxx, maxy = box
            rows.append({
                "geom": geom,
                "b": box,
                "area": max((maxx - minx) * (maxy - miny), 0.0),
                "name": props.get("name") or "",
                "name_zh": props.get("name_zh") or None,
                "iso": props.get("iso_a2") or "",
                "admin": props.get("admin") or "",
                "code": props.get("iso_3166_2") or "",
                "simple": None,
            })
        _rows = rows
        return _rows


def _simple(row):
    if row["simple"] is None:
        try:
            g = make_valid(shape(row["geom"])).simplify(0.08, preserve_topology=True)
            row["simple"] = None if g.is_empty else g
        except Exception:  # noqa: BLE001
            row["simple"] = None
        row["geom"] = None  # 简化后丢掉原始坐标，避免视野换一块就再占一份内存
    return row["simple"]


def query(west: float, south: float, east: float, north: float, zoom: float) -> tuple[list, bool]:
    """返回 (features, 数据是否已在磁盘上)。缩放小于 5 时不画线。"""
    path = config.DATA_DIR / "basemaps_raw" / "ne_10m_admin_1_states_provinces.geojson"
    if zoom < 5 or not path.exists():
        return [], path.exists()
    spans = [(west, east)] if west <= east else [(west, 180.0), (-180.0, east)]
    hits = []
    for r in _load():
        minx, miny, maxx, maxy = r["b"]
        if maxy < south or miny > north:
            continue
        if not any(maxx >= a and minx <= b for a, b in spans):
            continue
        hits.append(r)
    hits.sort(key=lambda r: r["area"], reverse=True)
    cap = 220 if zoom < 6 else 360
    out = []
    for r in hits[:cap]:
        g = _simple(r)
        if g is None:
            continue
        out.append({
            "type": "Feature",
            "properties": {
                "name": r["name"],
                "name_zh": r["name_zh"],
                "iso_a2": r["iso"],
                "admin": r["admin"],
                "iso_3166_2": r["code"],
                "era": "modern",
                "note": "Natural Earth 1:10m 现代一级行政区参考线，不是历史省界",
            },
            "geometry": mapping(g),
        })
    return out, True
