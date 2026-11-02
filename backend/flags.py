"""按日期的国旗（data/flags.json.gz：Wikidata P41 + 起止限定，经 data/curated/flag_overrides.json 修正）。"""
from __future__ import annotations

from functools import lru_cache

from .datafile import read_json
from .polity import valid_at


@lru_cache(maxsize=1)
def _flags(data_dir):
    return read_json(data_dir / "flags.json.gz", {}) or {}


def _tk(t):
    if not t:
        return None
    return (t["y"], t.get("m") or 0, t.get("d") or 0)


import re as _re
_RANGE = _re.compile(r"\((?:[^()]*?\s)?(1[5-9]\d\d|20\d\d)\s*[–—-]\s*(1[5-9]\d\d|20\d\d)\)")


def _name_ok(v, dk):
    """文件名自带年份范围（如「Flag of Nepal (1743–1962).svg」）时，只在该范围内（前后各放宽 1 年）使用：
    Wikidata 常把历史旗帜作为无日期语句挂在政权上，导致 1886 年显示 1985 年的旗。"""
    from urllib.parse import unquote
    m = _RANGE.search(unquote(v or "").replace("_", " "))
    if not m:
        return True
    a, b = int(m.group(1)), int(m.group(2))
    return a - 1 <= dk <= b + 1


def flag_at(data_dir, states, dk):
    """states：按优先顺序的政权 dict 列表（主要政权在前）。返回 (Commons 文件名, 是否有日期依据, 来源政权 id, 说明)；
    规则：先找当日有效的带日期语句（多条时取「首选」或起始最晚的）；没有任何带日期语句时用无日期语句；
    有带日期语句但都不覆盖所选日期时不显示（不拿别的年代的国旗充数）。"""
    F = _flags(data_dir)
    for st in states:
        lst = F.get(st["id"])
        if lst is None:
            continue
        lst = [x for x in lst if x.get("curated") or _name_ok(x.get("v"), dk)]
        dated = [x for x in lst if x.get("from") or x.get("to")]
        hits = [x for x in dated if valid_at(dk, x.get("from"), x.get("to"))]
        if hits:
            hits.sort(key=lambda x: (bool(x.get("curated")), bool(x.get("pref")), _tk(x.get("from")) or (-99999,)), reverse=True)
            return hits[0]["v"], True, st["id"], hits[0].get("src")
        und = [x for x in lst if not (x.get("from") or x.get("to"))]
        if und:
            und.sort(key=lambda x: bool(x.get("pref")), reverse=True)
            return und[0]["v"], False, st["id"], None
        return None, False, st["id"], "Wikidata 的国旗记录都不覆盖所选日期"
    for st in states:
        if st.get("flag") and st["id"] not in F:
            return st["flag"], False, st["id"], None
    return None, False, None, None
