"""实际控制 / 主权声索 / 国际承认。

每条陈述有日期和来源。几何只引用 data/curated/geom/status_areas.geojson
里的 Natural Earth 行政轮廓，或者标明交给已有的战争前线。没有轮廓的不画。
"""
from __future__ import annotations

import json

from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

from . import control_zones as CZ


def _read(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

ROLES = ("control", "claim", "recognition")
_front_cache: dict[float, object] = {}


def load(data_dir):
    doc = _read(data_dir / "curated" / "status_layers.json")
    gj = _read(data_dir / "curated" / "geom" / "status_areas.geojson")
    geoms = {}
    for f in gj.get("features") or []:
        gid = (f.get("properties") or {}).get("id")
        if not gid:
            continue
        g = make_valid(shape(f["geometry"]))
        p = g.representative_point()
        geoms[gid] = {"geom": g, "probe": [round(p.x, 4), round(p.y, 4)], "geojson": f["geometry"]}
    areas = []
    for a in doc.get("areas") or []:
        rec = dict(a)
        g = geoms.get(a.get("geom"))
        rec["_geom"] = g
        if a.get("geom") and g is None:
            raise RuntimeError(f"status area {a.get('id')} missing geometry {a.get('geom')}")
        areas.append(rec)
    return areas


def active_statements(area, dk):
    return [s for s in area.get("statements") or [] if CZ.active(s, dk)]


def _occupied(date, lon, lat):
    dk = round(date.key(), 5)
    if dk not in _front_cache:
        from backend.app import registry
        wf = registry.modules.get("war_fronts") if registry is not None else None
        geoms = []
        if wf is not None:
            data = wf.layer_query(None, date, {})
            for w in data.get("items") or []:
                for z in w.get("items") or []:
                    if z.get("kind") == "occupied" and z.get("geom"):
                        geoms.append(make_valid(shape(z["geom"])))
        _front_cache[dk] = unary_union(geoms) if geoms else None
        if len(_front_cache) > 24:
            _front_cache.pop(next(iter(_front_cache)))
    g = _front_cache[dk]
    if g is None:
        return None
    return bool(g.covers(Point(lon, lat)))


def _point_note(st, date, lon, lat):
    if st.get("assessed_by") != "war_fronts" or lon is None:
        return ""
    inside = _occupied(date, lon, lat)
    if inside is None:
        return "这一天的战争前线没有几何，该点对不上，标未知。"
    if inside:
        return "该点在当日战争前线的评估控制区内。"
    return "该点不在当日战争前线的评估控制区内。行政界和宣布的范围不能代替这一点。"


def rows_for(area, date, lon=None, lat=None):
    dk = date.key()
    rows = []
    for s in active_statements(area, dk):
        rows.append({
            "role": s.get("role"),
            "party": s.get("party"),
            "text": s.get("text") or "",
            "from": s.get("from"),
            "until": s.get("until"),
            "sources": s.get("sources") or [],
            "point": _point_note(s, date, lon, lat),
        })
    rows.sort(key=lambda r: ROLES.index(r["role"]) if r["role"] in ROLES else 9)
    return rows


def features_for(areas, date):
    dk = date.key()
    out = []
    for area in areas:
        g = area.get("_geom")
        if not g:
            continue
        sts = active_statements(area, dk)
        fills = [s for s in sts if s.get("draw") == "fill"]
        dashes = [s for s in sts if s.get("draw") == "dash"]
        if fills:
            s0 = fills[0]
            who = "、".join(s.get("party", {}).get("zh") for s in fills if (s.get("party") or {}).get("zh"))
            out.append({
                "id": area["id"] + "-control",
                "area": area["id"],
                "draw": "fill",
                "color_kind": s0.get("color_kind") or "occupied",
                "label": "实际控制" + (f"：{who}" if who else ""),
                "name_zh": area.get("name_zh"),
                "precision_zh": area.get("precision_zh"),
                "sources": s0.get("sources") or [],
                "geom": g["geojson"],
                "probe": g["probe"],
            })
        if dashes:
            who = "、".join(dict.fromkeys((s.get("party") or {}).get("zh") for s in dashes if (s.get("party") or {}).get("zh")))
            label = dashes[0].get("label") or ("声索" + (f"：{who}" if who else ""))
            src = []
            for s in dashes:
                for u in s.get("sources") or []:
                    if u not in src:
                        src.append(u)
            out.append({
                "id": area["id"] + "-claim",
                "area": area["id"],
                "draw": "dash",
                "color_kind": "claim",
                "label": label,
                "name_zh": area.get("name_zh"),
                "precision_zh": area.get("precision_zh"),
                "sources": src,
                "geom": g["geojson"],
                "probe": g["probe"],
            })
    return out


def hit(areas, date, lon, lat):
    pt = Point(lon, lat)
    found = []
    for area in areas:
        g = area.get("_geom")
        # 岸线简化后，紧贴海岸的城镇可能落在线外几百米。点选仍算这一块，画出的线不外扩。
        if not g or not g["geom"].buffer(0.003).covers(pt):
            continue
        rows = rows_for(area, date, lon, lat)
        if not rows:
            continue
        found.append({
            "id": area["id"],
            "name_zh": area.get("name_zh"),
            "precision_zh": area.get("precision_zh"),
            "probe": g["probe"],
            "rows": rows,
        })
    return found
