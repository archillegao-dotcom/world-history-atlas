"""欧洲、中国以外的历史区划。

几何只来自已经写进仓库的 OpenHistoricalMap 关系（CC0）。
按 start_date / end_date 决定画不画。没有合法几何的地区只返回「待考」，不拿今天的省界填。
"""
from __future__ import annotations

import json

from shapely.geometry import Point, shape

_CACHE: dict | None = None

# 点不在任何多边形里时，用这些框说明待考。先匹配面积小的框。
_BOXES = (
    ("ceylon", 79.5, 5.8, 82.0, 10.0, "锡兰省界"),
    ("taiwan", 120.0, 21.8, 122.1, 25.4, "台湾"),
    ("korea", 124.3, 33.8, 130.8, 43.2, "朝鲜"),
    ("japan", 128.5, 30.0, 146.0, 46.5, "日本"),
    ("karafuto", 141.0, 45.5, 145.8, 54.2, "桦太"),
    ("ottoman", 32.0, 12.0, 56.0, 32.5, "奥斯曼亚洲、非洲行省"),
    ("anatolia", 26.0, 36.0, 45.0, 42.2, "安纳托利亚"),
    ("central_asia", 50.0, 35.0, 80.0, 49.0, "俄属中亚"),
    ("british_india", 68.0, 8.0, 98.0, 37.0, "英属印度"),
    ("indochina", 102.0, 8.0, 109.8, 23.6, "印度支那"),
    ("mexico", -118.0, 14.0, -86.0, 32.8, "墨西哥"),
    ("us_state", -125.0, 24.0, -66.0, 49.5, "美国本土"),
    ("argentina", -73.0, -56.0, -53.0, -21.0, "阿根廷"),
    ("brazil", -74.0, -34.0, -34.0, 6.0, "巴西"),
    ("dei", 95.0, -11.0, 141.0, 8.0, "荷属东印度"),
    ("africa", -18.0, -35.0, 52.0, 37.0, "非洲"),
)


def view_day(date) -> tuple[str, str]:
    if date.m and date.d:
        return f"{date.y:04d}-{date.m:02d}-{date.d:02d}", ""
    if date.m:
        return f"{date.y:04d}-{date.m:02d}-01", "没有选日，按该月1日。不是该月1日发生了变化。"
    return f"{date.y:04d}-07-01", "没有选月日，按该年7月1日。不是该年7月1日发生了变化。"


def _in_box(lon: float, lat: float, west: float, south: float, east: float, north: float) -> bool:
    return west <= lon <= east and south <= lat <= north


def _europe(lon: float, lat: float) -> bool:
    if not (-25 <= lon <= 40 and lat >= 36):
        return False
    if 26 <= lon <= 45 and lat <= 42.2:
        return False
    return True


def _china(lon: float, lat: float) -> bool:
    if not (73 <= lon <= 135 and 18 <= lat <= 54):
        return False
    if _in_box(lon, lat, 124.3, 33.8, 130.8, 43.2):
        return False
    if _in_box(lon, lat, 120.0, 21.8, 122.1, 25.4):
        return False
    if _in_box(lon, lat, 128.5, 30.0, 146.0, 46.5):
        return False
    if _in_box(lon, lat, 102.0, 8.0, 109.8, 23.6):
        return False
    if _in_box(lon, lat, 68.0, 8.0, 98.0, 37.0):
        return False
    return True


def dataset(data_dir) -> dict:
    global _CACHE
    if _CACHE is not None and _CACHE.get("_dir") == str(data_dir):
        return _CACHE
    base = data_dir / "curated"
    raw = json.loads((base / "geom" / "hist_admin.geojson").read_text(encoding="utf-8"))
    pending = json.loads((base / "hist_admin_pending.json").read_text(encoding="utf-8"))
    features = []
    for feat in raw.get("features") or []:
        props = feat.get("properties") or {}
        if not props.get("from") or not props.get("until") or props["from"] >= props["until"]:
            continue
        if props.get("license") != "CC0 1.0":
            continue
        geom = feat.get("geometry")
        if not geom:
            continue
        try:
            shp = shape(geom)
        except Exception:
            continue
        if shp.is_empty:
            continue
        pt = shp.representative_point()
        props = dict(props)
        props["label"] = [round(pt.x, 3), round(pt.y, 3)]
        features.append({"props": props, "geom": geom, "shape": shp})
    features.sort(key=lambda row: row["shape"].area)
    _CACHE = {"_dir": str(data_dir), "features": features, "pending": pending}
    return _CACHE


def _on(props: dict, day: str) -> bool:
    return props["from"] <= day < props["until"]


def _label(props: dict) -> str:
    return props.get("name_zh") or props.get("name_en") or props.get("name") or "区划待考"


def features_for(pack: dict, day: str) -> list[dict]:
    out = []
    for row in pack["features"]:
        props = row["props"]
        if not _on(props, day):
            continue
        out.append({
            "id": props["id"],
            "name": _label(props),
            "name_en": props.get("name_en"),
            "region": props["region"],
            "kind": props.get("kind") or "",
            "from": props["from"],
            "until": props["until"],
            "label": props["label"],
            "license": props["license"],
            "source_url": props["source_url"],
            "precision": props["precision"],
            "date_note": props.get("date_note") or "",
            "geom": row["geom"],
        })
    return out


def _gap_text(pack: dict, region_id: str) -> str:
    for row in pack["pending"].get("gaps") or []:
        if row["id"] == region_id:
            return row["note"]
    return "区划待考。没有可再分发的当年边界，不画今天的行政区。"


def place_at(pack: dict, lon: float | None, lat: float | None, day: str) -> dict:
    if lon is None or lat is None:
        return {
            "status": "none",
            "name": None,
            "note": "先在地图上点一个地点。有几何的区划按日期画。没有合法几何的标区划待考。",
        }
    pt = Point(lon, lat)
    for row in pack["features"]:
        if not _on(row["props"], day):
            continue
        if row["shape"].covers(pt):
            props = row["props"]
            return {
                "status": "draw",
                "id": props["id"],
                "name": _label(props),
                "name_en": props.get("name_en"),
                "region": props["region"],
                "kind": props.get("kind") or "",
                "from": props["from"],
                "until": props["until"],
                "raw_start": props.get("raw_start"),
                "raw_end": props.get("raw_end"),
                "date_note": props.get("date_note") or "",
                "license": props["license"],
                "license_url": props.get("license_url"),
                "source_url": props["source_url"],
                "precision": props["precision"],
                "note": "这是当年有起止日期的区划。不是今天的行政区。",
            }
    if _europe(lon, lat):
        return {
            "status": "out",
            "name": None,
            "note": "欧洲各国的省界不在这一层。欧洲省界待考，不画今天的省界。",
        }
    if _china(lon, lat):
        return {
            "status": "out",
            "name": None,
            "note": "中国不在这一层。1912–1949 年有来源的省界在「省界与实控」。没有合法数据的年份仍是省界待考。",
        }
    hits = []
    for region_id, west, south, east, north, title in _BOXES:
        if _in_box(lon, lat, west, south, east, north):
            hits.append((region_id, (east - west) * (north - south), title))
    if not hits:
        return {
            "status": "none",
            "name": None,
            "note": "这一层没有收录这里的历史区划。没有合法几何就不画，不用今天的行政区代替。",
        }
    hits.sort(key=lambda item: item[1])
    region_id, _area, title = hits[0]
    text = _gap_text(pack, region_id)
    return {
        "status": "gap",
        "name": None,
        "region": region_id,
        "title": title,
        "note": text if "待考" in text else text + " 没有点中的那一块，区划待考。",
    }


def counts_for(pack: dict, day: str) -> dict:
    counts: dict[str, int] = {}
    for row in pack["features"]:
        if _on(row["props"], day):
            region = row["props"]["region"]
            counts[region] = counts.get(region, 0) + 1
    return counts
