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
    faction_path = base / "roc_faction_counties.json"
    faction = json.loads(faction_path.read_text(encoding="utf-8")) if faction_path.exists() else None
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
    _CACHE = {"meta": rules, "units": units, "faction": faction}
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


def _county_at(pack: dict, prov_id: str | None, lon: float, lat: float, day: str):
    """点落到 1931 年治所泰森格。只在山西、广西两省里找最近的治所。"""
    faction = pack.get("faction")
    if not faction or prov_id not in ("shanxi", "guangxi"):
        return None
    best = None
    best_d = 1e9
    counties = faction["counties"]
    for cid in faction["by_province"].get(prov_id) or []:
        cell = counties[cid]
        dx = cell["lon"] - lon
        dy = cell["lat"] - lat
        dist = dx * dx + dy * dy
        if dist < best_d:
            best_d = dist
            best = cell
    if best is None or best_d > 4:
        return None
    for span in best["spans"]:
        if _on(day, span.get("from"), span.get("until")):
            return {
                "id": best["id"],
                "name": best["name"],
                "actual": span.get("actual"),
                "certainty": span.get("certainty"),
                "from": span.get("from"),
                "until": span.get("until"),
                "note": span.get("note") or "",
                "sources": span.get("sources") or [],
            }
    return None


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
    county = _county_at(pack, unit.get("id"), lon, lat, day)
    bits = [shared]
    if unit.get("line_note"):
        bits.append(unit["line_note"])
    if control and control.get("note"):
        bits.append(control["note"])
    if county:
        bits.append(
            f"县域：{county['name']}（1931年治所）。实际控制：{county['actual']}。"
            f"标{county['certainty']}。{county['from']}起至{county['until']}。"
            f"{county['note']}"
        )
    sources = _sources(unit, control)
    for src in (county or {}).get("sources") or []:
        if src not in sources:
            sources.append(src)
    return {
        "status": "draw",
        "id": unit["id"],
        "name": named.get("name") or unit.get("name"),
        "kind": named.get("kind") or "",
        "nominal": _nominal(unit, day, control),
        "actual": control.get("actual") if control else ACTUAL_PENDING,
        "county": county,
        "scheme": unit.get("scheme") or "",
        "line_note": unit.get("line_note") or "",
        "sources": sources,
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
        "护国只标了1915-12-25的昆明县城点。1922年向赣的粤汉铁路收到6月17日。"
        "护法、第一次直奉、1926–1928北伐、1930年中原大战、蒋桂、中东路、热河、塘沽停战线、淞沪停战线、闽变、两广、西安、中央苏区、长征和冀东画了大致线，来源写明未核对《中華民國史事紀要》。"
        "这些线不是县界，也不是辖境。"
        "晋系和新桂系的填色用1931年治所县域，标大致或待考，不代替名义所属。"
        "九一八后的进占线收到1932-03-01，不改满洲国期间不画东北三省的规则。"
        "1938年10月有武汉会战的大致前线。"
        "1937年12月有南京保卫战的大致线，1944年11月有桂柳会战的大致线，1948年11月有淮海战役的大致线。"
        "伪政权只标名义和日军占领，不画新界，不改阵营。"
        "1937年12月10日南京不在日军占领层里，这一层从12月14日起。"
        "1949年省界面板按省会日写实际控制。云南从12月9日起不在西南底图块里。"
    )
