"""
不应作为地图政权候选的 Wikidata 条目 → data/curated/state_exclusions.json
  · 微型国家（Q188443 micronation）、虚构国家/虚构实体（Q1145276 fictional country、Q14897293 fictional entity、Q15632617 fictional human 等）
  · 只是文化/人群/考古学文化（Q465299 archaeological culture、Q41710 ethnic group、Q2472587 people、Q11042 culture）而非政权
经 QLever（Wikidata 全量）查询 P31/P279*，与 data/states.json.gz 求交。allow 列表里的条目即使命中也保留（人工核对）。
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from wdsparql import DATA, cached, qid, v
import gzip

CLASSES = {"Q188443": "微型国家", "Q1145276": "虚构国家", "Q14897293": "虚构实体", "Q465299": "考古学文化", "Q41710": "民族", "Q2472587": "人群",
           "Q11042": "文化", "Q15632617": "虚构人物", "Q3895768": "虚构地点"}
states = {s["id"] for s in json.load(gzip.open(DATA / "states.json.gz"))}
out = {}
for c, zh in CLASSES.items():
    rows = cached(f"excl_{c}", f"SELECT DISTINCT ?s WHERE {{ ?s wdt:P31/wdt:P279* wd:{c}. }}")
    hit = {qid(v(b, "s")) for b in rows} & states
    for q in hit:
        out.setdefault(q, []).append(zh)
    print(c, zh, len(rows), "in states:", len(hit))
p = DATA / "curated" / "state_exclusions.json"
old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
allow = old.get("allow", {})
res = {"_doc": __doc__.strip(), "allow": allow, "exclude": {q: r for q, r in sorted(out.items()) if q not in allow}}
p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("excluded", len(res["exclude"]))
