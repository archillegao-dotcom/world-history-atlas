"""补 OpenHistoricalMap 里 1918–1938 年捷克斯洛伐克的地（země）。

只收没有另标非 CC0 许可、并且带起止日期的关系。
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, shape

from add_ohm_admin import as_span, fetch, polygon_of
from build_europe_admin import clean_geom, dump_geom

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "geom" / "europe_admin.geojson"
IDS = [
    2856855, 2856854, 2856853, 2856852,
    2857446, 2857444, 2857445,
    2857443, 2857442, 2857441, 2857449, 2857483,
]
ZH = {
    "Země Česká": "捷克",
    "Země Moravská": "摩拉维亚",
    "Země Slezská": "西里西亚",
    "Země Moravskoslezská": "摩拉维亚-西里西亚",
    "Podkarpatská Rus": "喀尔巴阡鲁塞尼亚",
}
NOTE = (
    "OpenHistoricalMap 关系，数据库为 CC0。这是 1918–1938 年捷克斯洛伐克的地，不是 1867 年以前的王冠领地。"
    "斯洛伐克没有单独的关系。1938 年 9 月 30 日以后的捷克地没有沿用。"
    "https://www.openhistoricalmap.org/"
)


def main():
    data = json.loads(OUT.read_text(encoding="utf-8"))
    keep = {f"ohm-{i}" for i in IDS}
    features = [feat for feat in data["features"] if feat["properties"].get("id") not in keep]
    for element in fetch(IDS):
        tags = element.get("tags") or {}
        lic = (tags.get("license") or tags.get("licence") or "").lower()
        name = tags.get("name") or ""
        if lic and "cc0" not in lic:
            print("skip license", element["id"], name, lic)
            continue
        span = as_span(tags.get("start_date") or "", tags.get("end_date") or "")
        geom = clean_geom(polygon_of(element), 0.02) if span and name in ZH else None
        if geom is None or not span:
            print("skip geom", element["id"], name)
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"ohm-{element['id']}",
                "name_src": name,
                "name": ZH[name],
                "kind": "地",
                "nominal": "捷克斯洛伐克",
                "from": span[0],
                "until": span[1],
                "source_id": "ohm",
                "license": "CC0",
                "url": f"https://www.openhistoricalmap.org/relation/{element['id']}",
                "precision": NOTE,
            },
            "geometry": dump_geom(geom),
        })
    data["features"] = features
    gaps = [item for item in data.get("gaps") or [] if "捷克斯洛伐克的地" not in item and "瑞士州" not in item]
    gaps.append(
        "OpenHistoricalMap（CC0）补了 1918–1938 年捷克斯洛伐克的捷克、摩拉维亚、西里西亚和喀尔巴阡鲁塞尼亚。"
        "斯洛伐克没有关系，待考。1938-09-30 以后不沿用。"
        "瑞士州没有成套的带日期关系，待考。奥匈奥地利半部王冠领地和普鲁士各省已有 HistoGIS，不重复叠一份。"
        "荷兰、挪威、葡萄牙、匈牙利、南斯拉夫、罗马尼亚仍待考。"
    )
    data["gaps"] = gaps
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    units = [(shape(feat["geometry"]), feat["properties"]) for feat in features if feat["properties"]["id"] in keep]
    checks = [
        ("1925-06-01", 14.421, 50.087, "捷克"),
        ("1925-06-01", 16.608, 49.195, "摩拉维亚"),
        ("1930-06-01", 16.608, 49.195, "摩拉维亚-西里西亚"),
        ("1925-06-01", 22.295, 48.623, "喀尔巴阡鲁塞尼亚"),
        ("1910-06-01", 14.421, 50.087, None),
        ("1940-06-01", 14.421, 50.087, None),
    ]
    for day, lon, lat, expect in checks:
        point = Point(lon, lat)
        hits = [(geom.area, prop["name"]) for geom, prop in units if prop["from"] <= day < prop["until"] and geom.covers(point)]
        hits.sort()
        got = hits[0][1] if hits else None
        print(("OK" if got == expect else "DIFF"), day, expect, got)


if __name__ == "__main__":
    main()
