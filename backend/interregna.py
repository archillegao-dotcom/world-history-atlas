"""空位期、共治、摄政、权臣与对立君主（data/curated/interregna.json，tools/curated_src/interregna.py 生成）。
所选日期落在某个案例的起止之间、且所点政权（或同名合并的政权）在该案例的 states 中时，领导人面板顶部显示该时期实际掌权的人，
按史料所载的本官与角色标签（共治/摄政/权臣/临时执政……）列出；人物另有起止的，只显示所选日期在任的。"""
from __future__ import annotations

import json
from functools import lru_cache

from .timeutil import HDate


def _a(t):
    if not t.get("m"):
        return HDate(t["y"], 1, 1).key()
    return HDate(t["y"], t["m"], t.get("d") or 1).key()


def _b(t):
    if not t.get("m"):
        return HDate(t["y"], 12, 31).key()
    return HDate(t["y"], t["m"], t.get("d") or 28).key()


def valid_at(dk, a, b):
    """起止只精确到年/月时，按该年/月的第一天与最后一天计。结束日为后继者即位日：当天已不属于此时期。"""
    if a and dk < _a(a):
        return False
    if b:
        end = _b(b)
        return dk < end if b.get("d") else dk <= end
    return True


@lru_cache(maxsize=1)
def _cases(data_dir):
    p = data_dir / "curated" / "interregna.json"
    return json.loads(p.read_text(encoding="utf-8"))["cases"] if p.exists() else []


def _fmt(t):
    if not t:
        return None
    y = t["y"]
    s = f"公元前{-y}年" if y < 0 else f"{y}年"
    if t.get("m"):
        s += f"{t['m']}月"
        if t.get("d"):
            s += f"{t['d']}日"
    return s


def cases_at(data_dir, state_qids, dk, brief=None):
    out = []
    qs = set(state_qids)
    for c in _cases(data_dir):
        if not (qs & set(c["states"])) or not valid_at(dk, c["from"], c["to"]):
            continue

        def people(lst):
            r = []
            for p in lst:
                if not valid_at(dk, p.get("from") or c["from"], p.get("to") or c["to"]):
                    continue
                person = (brief(p["qid"]) if brief and p.get("qid") else None) or {}
                if not person.get("name"):
                    person = {"id": p.get("qid"), "name": p["zh"], "known": False}
                else:
                    person = {**person, "known": True, "name": p["zh"] if p["zh"] not in (person.get("name") or "") else person["name"]}
                r.append({"person": person, "office": p["office"], "tag": p["tag"], "note": p.get("note"),
                          "from": _fmt(p.get("from")), "to": _fmt(p.get("to"))})
            return r
        alt = c.get("alt")
        out.append({"id": c["id"], "title": c["title"], "kind": c["kind"], "from": _fmt(c["from"]), "to": _fmt(c["to"]),
                    "nominal": c.get("nominal"), "leaders": people(c["leaders"]), "note": c["note"], "src": c["src"],
                    "alt": {**alt, "leaders": people(alt["leaders"])} if alt else None})
    return out
