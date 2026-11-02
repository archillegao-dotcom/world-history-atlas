"""中国年号与君主本名（data/china_eras.json.gz，tools/build_china_eras.py 生成）+ 摄政/辅政者（data/curated/regents.json）。"""
from __future__ import annotations

import json
from functools import lru_cache

from .datafile import read_json
from .polity import valid_at


@lru_cache(maxsize=1)
def _d(data_dir):
    d = read_json(data_dir / "china_eras.json.gz", {}) or {}
    by_ruler = {}
    for e in d.get("eras", []):
        if e.get("ruler_qid"):
            by_ruler.setdefault(e["ruler_qid"], []).append(e)
    rp = data_dir / "curated" / "regents.json"
    regents = json.loads(rp.read_text(encoding="utf-8"))["regents"] if rp.exists() else []
    return d, by_ruler, regents


def personal_name(data_dir, qid):
    d, _, _ = _d(data_dir)
    r = (d.get("rulers") or {}).get(qid) or {}
    return r.get("name") if r.get("name") and r.get("name") != r.get("zh") else None


def eras_at(data_dir, ruler_qids, year):
    """所选年份正在使用的年号（按君主）；year 为历史纪年。"""
    d, by_ruler, _ = _d(data_dir)
    out = []
    for q in ruler_qids:
        for e in by_ruler.get(q, []):
            if e["from_y"] <= year <= e["to_y"]:
                out.append({"name": e["era_zh"], "py": e["era_py"], "from": e["from_y"], "to": e["to_y"], "ruler": e.get("ruler_zh"),
                            "note": e.get("note"), "src": d.get("src")})
    return out


def regents_at(data_dir, state_qids, dk):
    _, _, regents = _d(data_dir)
    return [r for r in regents if set(r["states"]) & set(state_qids) and valid_at(dk, r["from"], r["to"])]
