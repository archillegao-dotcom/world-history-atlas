"""《中華民國史事紀要》绝版 PDF 里已经对上印页的条目。

只读 data/curated/roc_shiji_daily.json。没有打开的册、没有对上的日子不写。
"""
from __future__ import annotations

import json

from shapely.geometry import Point

_CACHE: dict | None = None


def dataset(data_dir) -> dict:
    global _CACHE
    if _CACHE is None:
        p = data_dir / "curated" / "roc_shiji_daily.json"
        if not p.exists():
            _CACHE = {"items": [], "coverage_note": ""}
        else:
            _CACHE = json.loads(p.read_text(encoding="utf-8"))
    return _CACHE


def _on_day(item: dict, day: str, grain: str) -> bool:
    d = item.get("date") or ""
    if grain == "day":
        return d == day
    if grain == "month":
        return d.startswith(day)
    return d.startswith(day)


def _grain(date) -> tuple[str, str]:
    if date.m and date.d:
        return "day", f"{date.y:04d}-{date.m:02d}-{date.d:02d}"
    if date.m:
        return "month", f"{date.y:04d}-{date.m:02d}"
    return "year", f"{date.y:04d}"


def _inside(places, geom) -> bool:
    if geom is None:
        return True
    for p in places or []:
        if geom.contains(Point(p[0], p[1])):
            return True
    return False


def _cite(item: dict) -> str:
    vol = item.get("volume") or ""
    page = item.get("printed_page") or ""
    pdf = item.get("pdf_page")
    bits = [vol]
    if page:
        bits.append(f"印页{page}")
    if pdf:
        bits.append(f"PDF第{pdf}页")
    if item.get("edition_note"):
        bits.append(item["edition_note"])
    return "，".join(bits)


def news_items(data_dir, date, geom, limit: int) -> list[dict]:
    grain, key = _grain(date)
    out = []
    for item in dataset(data_dir).get("items") or []:
        if not item.get("news", True):
            continue
        if not _on_day(item, key, grain):
            continue
        places = item.get("places") or []
        if not _inside(places, geom):
            continue
        tags = [p[2] for p in places[:4] if len(p) > 2]
        out.append({
            "id": "shiji:" + item["id"],
            "title": item["title"],
            "title_en": None,
            "date": item["date"],
            "subtitle": " · ".join(x for x in [
                "史事紀要",
                ("类别：" + item["cat"]) if item.get("cat") else "",
                _cite(item),
                ("地点：" + "、".join(tags)) if tags else "",
            ] if x),
            "coord": [places[0][0], places[0][1]] if places else None,
            "match": "coord" if geom is not None else "world",
            "links": [{"label": "国史馆出版品", "url": item["catalog"]}] if item.get("catalog") else [],
            "score": 90,
        })
        if len(out) >= limit:
            break
    return out


def event_items(data_dir, day: str, geom) -> list[dict]:
    if geom is None:
        return []
    out = []
    for item in dataset(data_dir).get("items") or []:
        if not item.get("events", True):
            continue
        if item.get("date") != day:
            continue
        places = item.get("places") or []
        if not _inside(places, geom):
            continue
        out.append({
            "id": "shiji:" + item["id"],
            "title": item["title"],
            "title_en": "",
            "date": item["date"],
            "subtitle": (item.get("text") or "") + " " + _cite(item),
            "coord": [places[0][0], places[0][1]] if places else None,
            "match": "史事紀要",
            "coord_src": "curated",
            "links": [{"label": "国史馆出版品", "url": item["catalog"]}] if item.get("catalog") else [],
            "score": 85,
        })
    return out


def coverage_note(date) -> str:
    note = dataset_note_from_year(date.y)
    return note


def dataset_note_from_year(year: int) -> str:
    if not (1912 <= year <= 1949):
        return ""
    return "《中華民國史事紀要》只列入这一批已经对上印页的重大条目。没有条目不等于当天无事。目录里没有民国三十一年十月至十二月。"
