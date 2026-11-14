"""1912–1949 年中国省界和军阀实控。

几何来自 ENP-China / Virtual Shanghai 的 CC0 省界。同一编号在各年份档里是同一条线。
画不画、叫什么、名义上属于谁、实际上谁在控制，都按本文件里的日期，不拿今天的省界填。
"""
from __future__ import annotations

import json

from shapely.geometry import Point, shape

_CACHE: dict | None = None

DEFAULT_DRAW = [{"from": "1912-01-01", "until": "1950-01-01"}]
DEFAULT_NOMINAL = [
    {"from": "1912-01-01", "until": "1928-06-08", "name": "北京政府"},
    {"from": "1928-06-08", "until": "1950-01-01", "name": "南京国民政府"},
]
PENDING = "省界待考"
ACTUAL_PENDING = "实控待考"
NOMINAL_PENDING = "名义所属待考"


def view_day(date) -> tuple[str, str]:
    if date.m and date.d:
        return f"{date.y:04d}-{date.m:02d}-{date.d:02d}", ""
    if date.m:
        return f"{date.y:04d}-{date.m:02d}-01", "没有选日，按该月1日。不是该月1日发生了变化。"
    return f"{date.y:04d}-07-01", "没有选月日，按该年7月1日。不是该年7月1日发生了变化。"


def _on(day: str, start: str | None, end: str | None) -> bool:
    if start and day < start:
        return False
    if end and not (day < end):
        return False
    return True


def _span(rows, day: str):
    for row in rows or []:
        if _on(day, row.get("from"), row.get("until")):
            return row
    return None


def _expand(unit: dict) -> None:
    if "names" not in unit:
        unit["names"] = [{
            "from": "1912-01-01", "until": "1950-01-01",
            "name": unit["name"], "kind": "省",
        }]
    if "draw" not in unit:
        unit["draw"] = list(DEFAULT_DRAW)
    if "nominal" not in unit:
        unit["nominal"] = list(DEFAULT_NOMINAL)
    unit.setdefault("controls", [])
    unit.setdefault("gaps", [])
    unit.setdefault("sources", [])
    unit.setdefault("line_note", "")
    if unit["sid"].startswith("1947-") and unit["id"] != "taiwan":
        unit.setdefault("scheme", "1947东北九省")
    if unit["id"] == "fengtian":
        unit.setdefault("scheme", "东北三省")


def dataset(data_dir) -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    base = data_dir / "curated"
    rules = json.loads((base / "roc_admin.json").read_text(encoding="utf-8"))
    geoms = json.loads((base / "roc_admin_geom.json").read_text(encoding="utf-8"))
    by_sid = {row["sid"]: row for row in geoms["units"]}
    units = []
    for unit in rules["units"]:
        geom = by_sid.get(unit["sid"])
        if not geom:
            raise RuntimeError(f"省界几何缺少 {unit['sid']}")
        _expand(unit)
        unit["geom"] = geom["geom"]
        unit["label"] = geom["label"]
        unit["_shape"] = shape(geom["geom"])
        units.append(unit)
    _CACHE = {"meta": rules, "units": units}
    return _CACHE


def _control(unit: dict, day: str):
    return _span(unit.get("controls"), day)


def _nominal(unit: dict, day: str, control) -> str:
    if control:
        cut = control.get("nominal_until")
        if cut and not (day < cut):
            return control.get("nominal_after") or NOMINAL_PENDING
        if control.get("nominal"):
            return control["nominal"]
    row = _span(unit.get("nominal"), day)
    if row and row.get("name"):
        return row["name"]
    return NOMINAL_PENDING


def _name(unit: dict, day: str):
    return _span(unit.get("names"), day) or {}


def _drawn(unit: dict, day: str) -> bool:
    return _span(unit.get("draw"), day) is not None


def _gap(unit: dict, day: str):
    return _span(unit.get("gaps"), day)


def _rank(unit: dict, day: str) -> str:
    if _drawn(unit, day):
        return "draw"
    if _gap(unit, day):
        return "gap"
    return "outside"


def locate(units, lon: float, lat: float, day: str):
    pt = Point(lon, lat)
    covered = [u for u in units if u["_shape"].covers(pt)]
    drawn = [u for u in covered if _rank(u, day) == "draw"]
    if drawn:
        drawn.sort(key=lambda u: (_span(u["draw"], day) or {}).get("from") or "")
        return drawn[-1], "draw"
    gaps = [u for u in covered if _rank(u, day) == "gap"]
    if gaps:
        return gaps[0], "gap"
    return None, "none"


def _sources(unit: dict, control) -> list[str]:
    out = []
    for src in (control or {}).get("sources") or []:
        if src not in out:
            out.append(src)
    for src in unit.get("sources") or []:
        if src not in out:
            out.append(src)
    return out


def features_for(units, day: str) -> list[dict]:
    out = []
    for unit in units:
        if not _drawn(unit, day):
            continue
        named = _name(unit, day)
        control = _control(unit, day)
        out.append({
            "id": unit["id"],
            "name": named.get("name") or unit.get("name"),
            "kind": named.get("kind") or "",
            "actual": control.get("actual") if control else None,
            "scheme": unit.get("scheme") or "",
            "label": unit["label"],
            "geom": unit["geom"],
        })
    return out


def place_at(pack, lon: float | None, lat: float | None, day: str) -> dict:
    if lon is None or lat is None:
        return {"status": "none", "name": None, "kind": "", "nominal": None, "actual": None,
                "scheme": "", "note": "先在地图上点一个地点。", "line_note": "", "sources": []}
    unit, status = locate(pack["units"], lon, lat, day)
    shared = pack["meta"].get("line_note") or ""
    if status == "none" or unit is None:
        return {
            "status": "none", "name": None, "kind": "", "nominal": None, "actual": None,
            "scheme": "", "line_note": "", "sources": [],
            "note": "省界待考。这里没有可再分发的当年省界，不画今天的省界。",
        }
    if status == "gap":
        gap = _gap(unit, day) or {}
        return {
            "status": "gap", "name": None, "kind": "", "nominal": None, "actual": None,
            "scheme": unit.get("scheme") or "", "line_note": unit.get("line_note") or "",
            "sources": _sources(unit, None),
            "note": gap.get("note") or "省界待考。不画今天的省界。",
        }
    named = _name(unit, day)
    control = _control(unit, day)
    bits = [shared]
    if unit.get("line_note"):
        bits.append(unit["line_note"])
    if control and control.get("note"):
        bits.append(control["note"])
    return {
        "status": "draw",
        "id": unit["id"],
        "name": named.get("name") or unit.get("name"),
        "kind": named.get("kind") or "",
        "nominal": _nominal(unit, day, control),
        "actual": control.get("actual") if control else ACTUAL_PENDING,
        "scheme": unit.get("scheme") or "",
        "line_note": unit.get("line_note") or "",
        "sources": _sources(unit, control),
        "note": "".join(bits),
    }


def coverage_note(meta: dict) -> str:
    rejected = "、".join(row["name"] for row in meta.get("license_rejected") or [])
    listed = "；".join(meta.get("not_this_batch") or [])
    return (
        "省界用 ENP-China / Virtual Shanghai 的 CC0 轮廓。同一编号在五个年份档里是同一条线，不是逐年新测。"
        "建省、改名和中间不画的年份按日期处理。没有这条线的年份和地区标省界待考，不画今天的省界。"
        f"没有使用：{rejected}。"
        f"全球同类本批只列清单，没有画：{listed}。"
        "内战只画已经核对到页的大致走廊和进军线，不是疆域，也不是县界。"
        "县城点来自 MCGD_Rep（CC BY 4.0），是1931年的县城，不是县界。"
        "护国只标了1915-12-25的昆明县城点。1922-05-13画了向赣的粤汉铁路大致线。1932-02-04画了上海一端的沪宁、沪杭大致线。"
        "护法、第一次直奉、1926年北伐进军线没有画到县。"
    )
