"""国家政权/国号更替链（data/curated/regime_chains.json，tools/curated_src/regime_chains.py 生成；每行注明来源）。"""
from __future__ import annotations

from functools import lru_cache

import json


def _k(s):
    if not s:
        return None
    y, m, d = (int(x) for x in s.split("-"))
    return y + (m - 1) / 12 + d / 372   # 与 HDate.key() 一致


@lru_cache(maxsize=1)
def _load(data_dir):
    p = data_dir / "curated" / "regime_chains.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    ch = d.get("chains", {})
    by_q = {}
    for cq, c in ch.items():
        by_q.setdefault(cq, cq)
        for r in c["rows"]:
            if r.get("qid"):
                by_q.setdefault(r["qid"], cq)
    return ch, by_q


def chain_for(data_dir, qids, dk):
    """qids：主要政权及同名候选。返回 {"country", "country_zh", "rows":[...含 current], "now":[当前行], "merge_country"} 或 None。"""
    ch, by_q = _load(data_dir)
    cq = next((by_q[q] for q in qids if q in by_q), None)
    if not cq:
        return None
    c = ch[cq]
    rows = []
    for r in c["rows"]:
        a, b = _k(r["from"]), _k(r["to"])
        cur = (a is None or a <= dk) and (b is None or dk < b)
        rows.append({**r, "current": cur})
    now = [r for r in rows if r["current"]]
    return {"country": cq, "country_zh": c["zh"], "rows": rows, "now": now, "merge_country": c.get("merge_country", True)}
