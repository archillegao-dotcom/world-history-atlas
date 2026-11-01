#!/usr/bin/env python3
"""
资源点（「经济与资源」图层的资源部分）：Wikidata 中有坐标的矿山（mine Q820477）、油田（oil field Q211748）、
天然气田（natural gas field Q1349255）及其子类，至少 2 个语言版本的维基条目（保持适度规模、知名度较高）。
字段：坐标 P625、开始 P571（或 P580）、关闭 P576（或 P582）、产品 P1056、所在国家 P17、类型、维基条目。
输出 data/resources.json.gz。
"""
from __future__ import annotations

import collections

from build_states import labels_for, q
from wdsparql import DATA, parse_point, parse_time, pick_zh, qid, simplifier, v, write_gz, cached

t2s = simplifier()
ROOTS = {"Q820477": "mine", "Q211748": "oil", "Q1349255": "gas"}
MIN_SL = 2


def main():
    recs = {}
    for root, kind in ROOTS.items():
        for b in q(f"rs_core_{root}", f"?x wdt:P31/wdt:P279* wd:{root}; wikibase:sitelinks ?sl; wdt:P625 ?c. FILTER(?sl >= {MIN_SL})", "?x ?sl ?c", ""):
            k = qid(v(b, "x"))
            pt = parse_point(v(b, "c"))
            if not pt:
                continue
            r = recs.setdefault(k, {"id": k, "sl": int(v(b, "sl")), "coord": [round(pt[0], 3), round(pt[1], 3)], "kind": kind})
            if kind != "mine":           # 同时属于矿山和油气田时按油气标注
                r["kind"] = kind
    print("resources:", len(recs), collections.Counter(r["kind"] for r in recs.values()), flush=True)
    ids = sorted(recs)
    for k in range(0, len(ids), 3000):
        sub = {x: recs[x] for x in ids[k:k + 3000]}
        core = "VALUES ?x { " + " ".join(f"wd:{x}" for x in sub) + " }"
        labels_for(f"rs{k}", core, "x", sub)
        for prop, fld in (("P571", "from"), ("P580", "from"), ("P576", "to"), ("P582", "to")):
            for b in q(f"rs{k}_{prop}", core, "?x ?d ?dp", f"?x p:{prop}/psv:{prop} ?tv. ?tv wikibase:timeValue ?d; wikibase:timePrecision ?dp."):
                r = recs[qid(v(b, "x"))]
                t = parse_time(v(b, "d"), v(b, "dp"))
                if t and fld not in r:
                    r[fld] = t
        prods = collections.defaultdict(list)
        for b in q(f"rs{k}_P1056", core, "?x ?p ?l", '?x wdt:P1056 ?p. ?p rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-hans","zh-cn","en"))'):
            prods[(qid(v(b, "x")), qid(v(b, "p")))].append((b["l"]["xml:lang"], b["l"]["value"]))
        for (x, p), ls in prods.items():
            d = dict(ls)
            z, _ = pick_zh(d)
            name = t2s(z) if z else d.get("en")
            lst = recs[x].setdefault("products", [])
            if name and name not in lst:
                lst.append(name)
        for b in q(f"rs{k}_P17", core, "?x ?c", "?x wdt:P17 ?c."):
            recs[qid(v(b, "x"))].setdefault("country", qid(v(b, "c")))
    write_gz(DATA / "resources.json.gz", sorted(recs.values(), key=lambda r: -r["sl"]))
    print("with start date:", sum(1 for r in recs.values() if r.get("from")))


if __name__ == "__main__":
    main()
