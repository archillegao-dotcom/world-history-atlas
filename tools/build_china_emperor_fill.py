"""补「中国皇帝」(Wikidata Q268218) 任职记录中缺 P1001 管辖区（或只写到上级条目，如「汉朝」Q7209）的任职者：
按任职开始日期对应到 data/curated/china_dynasties.json 的主朝代，且只在该朝代当时没有其他在位记录时补入（避免把并立政权的皇帝补进主朝代）。
1912 年以后的不补。输出 data/ruler_fills.json.gz（由 backend/polity.py 合并）。日期、人物均取自 Wikidata（CC0）。"""
import sys, json, gzip, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import wdsparql as W
from backend import config
from backend.polity import PolityResolver
from backend.timeutil import rec_key

R = PolityResolver(config.DATA_DIR)
dyn = json.loads((ROOT / "data/curated/china_dynasties.json").read_text(encoding="utf-8"))
allq = set(dyn["main"]) | set(dyn["secondary"])
q = """SELECT ?p ?s ?sp ?e ?ep ?j ?zh ?en ?b ?d WHERE {
 ?p p:P39 ?st . ?st ps:P39 wd:Q268218 ; wikibase:rank ?rank . FILTER(?rank != wikibase:DeprecatedRank)
 ?st pqv:P580 ?sv . ?sv wikibase:timeValue ?s ; wikibase:timePrecision ?sp .
 OPTIONAL { ?st pqv:P582 ?ev . ?ev wikibase:timeValue ?e ; wikibase:timePrecision ?ep . }
 OPTIONAL { ?st pq:P1001 ?j }
 OPTIONAL { ?p rdfs:label ?zh FILTER(lang(?zh) = "zh") } OPTIONAL { ?p rdfs:label ?en FILTER(lang(?en) = "en") }
 OPTIONAL { ?p wdt:P569 ?b } OPTIONAL { ?p wdt:P570 ?d }
}"""
rows = W.sparql(W.PREFIXES + q)
office = {o["id"]: o for o in R.offices}
# 只补管辖区缺失或只写到上级条目的记录：汉朝 Q7209、宋朝 Q7462、帝制中国 Q12060881
PARENTS = {None, "Q7209", "Q7462", "Q12060881"}
# 并立/起事政权的称帝者（Wikidata 只写了「汉朝」或没写管辖区），不属于主朝代
EXCLUDE = {"Q7265": "刘盆子：赤眉军所立的建世帝（25–27），与东汉光武帝并立",
           "Q890338": "侯景：551 年篡梁自立为「汉」皇帝，不是梁朝皇帝"}
fills, persons, seen = [], {}, set()
for b in rows:
    j = W.qid(W.v(b, "j"))
    if j not in PARENTS:      # 管辖区是别的政权（如大顺、西凉）：不是主朝代的皇帝
        continue
    p = W.qid(W.v(b, "p"))
    if p in EXCLUDE:
        continue
    f = W.parse_time(W.v(b, "s"), W.v(b, "sp"))
    t = W.parse_time(W.v(b, "e"), W.v(b, "ep"))
    if not f or f["y"] >= 1912 or (p, f["y"]) in seen:
        continue
    k = rec_key(f) + 1 / 365
    sk = lambda d: d["y"] if not d.get("m") else rec_key(d)   # 只到年精度的朝代起始日按该年年初
    main = [s for s in dyn["main"] if s in R.states and R.states[s].get("from") and sk(R.states[s]["from"]) <= k
            and (not R.states[s].get("to") or k <= rec_key(R.states[s]["to"]))]
    if not main:
        continue
    S = max(main, key=lambda s: rec_key(R.states[s]["from"]))   # 交替之年取新朝代（如 960 年取北宋而非后周）
    oid = f"Q268218@{S}"
    hs = office.get(oid, {}).get("holders", [])
    if any(h["p"] == p for h in hs):
        continue
    busy = any(h.get("from") and rec_key(h["from"]) <= k and (not h.get("to") or k <= rec_key(h["to"])) for h in hs)
    if busy:
        print("skip (gap filled already)", p, W.v(b, "zh"), f, S)
        continue
    seen.add((p, f["y"]))
    fills.append({"office": oid, "state": S, "state_zh": R.states[S].get("zh"), "p": p, "from": f, "to": t,
                  "juris_raw": j, "source": f"https://www.wikidata.org/wiki/{p}#P39"})
    if p not in R.persons:
        persons[p] = {"id": p, "zh": W.v(b, "zh"), "en": W.v(b, "en"),
                      "born": W.parse_time(W.v(b, "b"), "9") if W.v(b, "b") else None,
                      "died": W.parse_time(W.v(b, "d"), "9") if W.v(b, "d") else None}
    print("fill", oid, R.states[S].get("zh"), p, W.v(b, "zh"), f, t, "P1001=", j)
with gzip.open(ROOT / "data/ruler_fills.json.gz", "wt", encoding="utf-8") as fh:
    json.dump({"fills": fills, "persons": list(persons.values())}, fh, ensure_ascii=False)
print("fills", len(fills), "new persons", len(persons))
