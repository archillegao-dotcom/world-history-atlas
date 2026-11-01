#!/usr/bin/env python3
"""重点国家关键职位的任期覆盖率（合并官方/维基名单前后）→ data/audit/official_coverage.json
覆盖率 = 职位存续期（最早任期开始 → 最晚任期结束或今天）中，有至少一位带日期任职者的天数占比。
「合并前」只算 Wikidata 原有任期（没有 src 字段的任职记录），「合并后」包括 tools/build_official_offices.py 补充的记录。"""
import datetime, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config
from backend.polity import PolityResolver
from backend.timeutil import rec_key

PRIORITY = [("中华民国", ["Q887003", "Q702650", "Q7241342"]), ("中华人民共和国", ["Q655407", "Q4122271", "Q849418", "Q2708520"]),
            ("美国", ["Q11696", "Q14213"]), ("英国", ["Q14211", "Q9134365"]), ("法国", ["Q191954", "Q1587677"]),
            ("德国", ["Q56022", "Q25223"]), ("俄罗斯/苏联", ["Q218295", "Q842386", "Q462189", "Q1048744", "Q135215773"]),
            ("日本", ["Q274948", "Q208233"]), ("韩国", ["Q6296418", "Q15407843"]), ("澳门（葡治）", ["Q907213"])]
NOW = rec_key({"y": datetime.date.today().year, "m": datetime.date.today().month, "d": datetime.date.today().day})


def cover(hs, lo, hi):
    iv = sorted((max(lo, rec_key(h["from"])), min(hi, rec_key(h["to"]) if h.get("to") else NOW)) for h in hs if h.get("from"))
    tot, cur = 0.0, None
    for a, b in iv:
        if b <= a:
            continue
        if cur and a <= cur[1]:
            cur[1] = max(cur[1], b)
        else:
            if cur: tot += cur[1] - cur[0]
            cur = [a, b]
    if cur: tot += cur[1] - cur[0]
    return round(100 * tot / (hi - lo), 1) if hi > lo else 0.0


def main():
    R = PolityResolver(config.DATA_DIR)
    by = {o["id"]: o for o in R.offices}
    rows = []
    for country, ids in PRIORITY:
        for q in ids:
            o = by.get(q)
            if not o:
                rows.append({"country": country, "office": q, "missing": True}); continue
            hs = o.get("holders", [])
            dated = [h for h in hs if h.get("from")]
            if not dated:
                rows.append({"country": country, "office": q, "name": o.get("zh") or o.get("en"), "before": 0, "after": 0, "holders": len(hs)}); continue
            lo = min(rec_key(h["from"]) for h in dated)
            ends = [rec_key(h["to"]) if h.get("to") else NOW for h in dated]
            hi = max(ends)
            before = [h for h in hs if not h.get("src")]
            rows.append({"country": country, "office": q, "name": o.get("zh") or o.get("en"), "span": [int(lo), int(hi)],
                         "holders_before": sum(1 for h in before if h.get("from")), "holders_after": len(dated),
                         "before": cover(before, lo, hi), "after": cover(hs, lo, hi),
                         "sources": [s["url"] for s in o.get("sources", [])]})
    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds"), "rows": rows, "merge_stats": R.official_stats}
    (config.DATA_DIR / "audit" / "official_coverage.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(r.get("country"), r.get("office"), r.get("name"), r.get("span"), r.get("holders_before"), "->", r.get("holders_after"), f"{r.get('before')}% -> {r.get('after')}%")


if __name__ == "__main__":
    main()
