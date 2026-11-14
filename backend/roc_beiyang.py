"""已经核对到页的内战走廊和县城点。

目前包括 1912–1928 的若干走廊，以及 1932-02-04 的上海铁路方向。

省界仍在 roc_admin。这里只加有出处的折线和点。
折线是大致走廊或进军方向，不是疆域，也不是县界。
县城点来自 MCGD_Rep（CC BY 4.0），是 1931 年的县城，不是县界。
没有页证的日子不画。
"""
from __future__ import annotations

import json

from shapely.geometry import Point

_CACHE: dict | None = None


def dataset(data_dir) -> dict:
    global _CACHE
    if _CACHE is None:
        p = data_dir / "curated" / "roc_beiyang.json"
        _CACHE = json.loads(p.read_text(encoding="utf-8"))
    return _CACHE


def _on(day: str, start: str | None, end: str | None) -> bool:
    if start and day < start:
        return False
    if end and not (day < end):
        return False
    return True


def _public(row: dict, keys: tuple[str, ...]) -> dict:
    return {k: row.get(k) for k in keys}


def bundle(data_dir, day: str) -> dict:
    data = dataset(data_dir)
    wars = [w for w in data["wars"] if _on(day, w.get("from"), w.get("until"))]
    fronts = [f for f in data["fronts"] if _on(day, f.get("from"), f.get("until"))]
    seats = [s for s in data["seats"] if _on(day, s.get("from"), s.get("until"))]
    return {
        "wars": wars,
        "fronts": fronts,
        "seats": seats,
        "county_license": data["county_source"]["license"],
        "county_url": data["county_source"]["url"],
    }


def for_province(data_dir, day: str, province: str | None) -> dict:
    raw = bundle(data_dir, day)
    if not province:
        return {"wars": [], "fronts": [], "seats": [], "county_license": raw["county_license"], "county_url": raw["county_url"]}
    wars = [w for w in raw["wars"] if province in (w.get("provinces") or [])]
    war_ids = {w["id"] for w in wars}
    fronts = [f for f in raw["fronts"] if f.get("war") in war_ids]
    seats = [s for s in raw["seats"] if s.get("province") == province]
    return {
        "wars": wars,
        "fronts": fronts,
        "seats": seats,
        "county_license": raw["county_license"],
        "county_url": raw["county_url"],
    }


def events_for(data_dir, day: str, geom) -> list[dict]:
    if geom is None:
        return []
    out = []
    for ev in dataset(data_dir)["events"]:
        if not _on(day, ev.get("from"), ev.get("until")):
            continue
        hit = False
        for lon, lat in ev.get("coords") or []:
            if geom.contains(Point(lon, lat)):
                hit = True
                break
        if not hit:
            continue
        out.append({
            "id": "roc:" + ev["id"],
            "title": ev["title"],
            "title_en": "",
            "date": ev["from"] + (f" — {ev['until']}" if ev.get("until") else ""),
            "subtitle": "本批核对 " + (ev.get("desc") or ""),
            "coord": (ev.get("coords") or [None])[0],
            "match": "民国史事",
            "coord_src": "curated",
            "links": [{"label": "来源", "url": url} for url in ev.get("sources") or []],
            "score": 80,
        })
    return out
