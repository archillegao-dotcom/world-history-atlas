"""
模块共用工具：读取缓存数据、点在面内过滤、国籍/国家 QID 兜底匹配、生成来源链接。
（文件名以 _ 开头，不会被当作模块注册。）
"""
from __future__ import annotations

from ..datafile import read_json
import gzip
import json
import re
from pathlib import Path

from shapely.geometry import Point

from ..timeutil import HDate, PRECISION_ZH


def load_records(path: Path) -> list[dict]:
    """读取 .json.gz（或打包版中的同名 .json.xz）记录列表；都不存在时返回空列表。"""
    return read_json(path, [])


def load_country_names(ctx) -> dict[str, list[str]]:
    """data/countries.json: {QID: {"names": [英文名, 中文名, 别名...], "coord": [lon, lat]}}，由 tools/build_wikidata.py 生成。
    用于没有坐标的条目按「国家/国籍」与地图政权名称兜底匹配。"""
    if "countries" not in ctx.shared:
        f = Path(ctx.data_dir) / "countries.json"
        ctx.shared["countries"] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return ctx.shared["countries"]


def norm(s: str | None) -> str:
    s = (s or "").lower()
    s = re.sub(r"^(the |kingdom of |empire of |republic of )", "", s)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", s)


def polity_names(polity: dict) -> set[str]:
    p = polity["props"]
    return {norm(p.get(k)) for k in ("NAME", "ABBREVN", "SUBJECTO", "PARTOF") if p.get(k)} - {""}


def matches_polity(rec: dict, polity: dict | None, countries: dict, allow_country: bool = True) -> str | None:
    """返回匹配方式：'coord'（坐标落在多边形内）、'country'（国家/国籍名称与政权名称一致），否则 None。
    有坐标时只用坐标判断（跨时代最稳健）；没有坐标才退回名称匹配。"""
    if polity is None:
        return "world"
    c = rec.get("coord")
    if c:
        return "coord" if polity["geom"].contains(Point(c[0], c[1])) else None
    if allow_country and rec.get("countries"):
        names = polity_names(polity)
        for q in rec["countries"]:
            c = countries.get(q, {})
            cn = c.get("names", []) if isinstance(c, dict) else c
            if any(norm(n) in names for n in cn):
                return "country"
    return None


def match_any(rec: dict, polity: dict | None, countries: dict) -> str | None:
    """同 matches_polity，但会依次检查主坐标与额外候选坐标 rec["coords"]（参与方、多个国家）。"""
    if polity is None:
        return "world"
    pts = ([rec["coord"]] if rec.get("coord") else []) + rec.get("coords", [])
    if pts:
        for c in pts:
            if polity["geom"].contains(Point(c[0], c[1])):
                return "coord"
        return None
    return matches_polity(rec, polity, countries)


def fmt_time(t: dict | None) -> str:
    if not t:
        return "?"
    s = HDate(t["y"], t.get("m", 0), t.get("d", 0)).label_zh()
    p = t.get("p", 9)
    if p < 9:
        s += f"（精度：{PRECISION_ZH.get(p, '粗略')}）"
    return s


def links(rec: dict) -> list[dict]:
    out = [{"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{rec['id']}"}]
    if rec.get("zhwiki"):
        out.append({"label": "中文维基", "url": rec["zhwiki"]})
    if rec.get("enwiki"):
        out.append({"label": "English Wikipedia", "url": rec["enwiki"]})
    return out
