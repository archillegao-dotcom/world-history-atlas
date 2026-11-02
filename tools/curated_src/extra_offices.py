"""补充职位（v0.6.1）：实际掌权者、与名义君主并立的职位（幕府将军、摄政/关白、执权、护国公）。
从 Wikidata SPARQL 取 P39 任职记录（起止限定 P580/P582）与人物 zh/en 标签 → data/curated/extra_offices.json。
用法：.venv/bin/python tools/curated_src/extra_offices.py"""
import json, time, urllib.parse, urllib.request
OFFICES = {   # 职位 QID: (显示名, 管辖政权 QID 列表, 备注)
    "Q131767": ("征夷大将军（幕府将军）", ["Q736839", "Q1154406", "Q205662", "Q17"], "幕府将军：镰仓、室町、江户幕府的实际最高统治者，天皇为名义君主"),
    "Q1199966": ("关白", ["Q17"], "关白：成年天皇的辅政者，平安时代藤原氏摄关政治的核心职位"),
    "Q96046808": ("摄政（日本）", ["Q17"], "摄政：天皇年幼或女性天皇时代行政务"),
    "Q1045904": ("执权", ["Q736839", "Q17"], "执权：镰仓幕府将军的辅佐，北条氏世袭，为幕府实际掌权者"),
    "Q512196": ("护国公", ["Q330362"], "护国公：1653–1659 年英格兰、苏格兰和爱尔兰联邦的国家元首"),
    # 北洋政府时期（1912–1928）的总统与国务总理：Wikidata 把这两个职位只记在「中华民国」Q865 下，地图上 1912–1949 的中华民国是 Q13426199
    "Q887003": ("中华民国大总统（北洋政府）", ["Q13426199"], "北洋政府时期的中华民国大总统（1928 年以前）；只取 1928 年以前就任的记录"),
    "Q702650": ("国务总理（北洋政府）", ["Q13426199"], "北洋政府时期的国务总理（1928 年以前）；只取 1928 年以前就任的记录"),
}
YEAR_MAX = {"Q887003": 1928, "Q702650": 1928}
EXCLUDE = {}
UA = {"User-Agent": "WHA-audit/0.6.1 (world history atlas; offline build)", "Accept": "application/sparql-results+json"}
def q(sparql):
    u = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": sparql})
    for k in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90))["results"]["bindings"]
        except Exception as e:
            print("retry", e); time.sleep(5 * (k + 1))
    raise SystemExit("sparql failed")
def t(v):
    if not v: return None
    s, p = v["value"], None
    neg = s.startswith("-"); s = s.lstrip("+-")
    y, m, d = s[:s.index("-", 1)], s.split("-")[1], s.split("-")[2][:2]
    return {"y": -int(y) if neg else int(y), "m": int(m), "d": int(d), "p": 11}
out = {"_doc": __doc__, "offices": []}
import sys
only = sys.argv[1:]
old = {o["id"]: o for o in json.load(open("data/curated/extra_offices.json"))["offices"]} if only else {}
for oid, (zh, juris, note) in OFFICES.items():
    if only and oid not in only:
        out["offices"].append(old[oid]); continue
    rows = q(f"""SELECT ?p ?zh ?en ?a ?ap ?b ?bp WHERE {{ ?p p:P39 ?s. ?s ps:P39 wd:{oid}.
      OPTIONAL {{ ?s pqv:P580 ?av. ?av wikibase:timeValue ?a; wikibase:timePrecision ?ap. }}
      OPTIONAL {{ ?s pqv:P582 ?bv. ?bv wikibase:timeValue ?b; wikibase:timePrecision ?bp. }}
      OPTIONAL {{ ?p rdfs:label ?zh FILTER(LANG(?zh) IN ("zh","zh-hans","zh-cn")) }}
      OPTIONAL {{ ?p rdfs:label ?en FILTER(LANG(?en)="en") }} }}""")
    hs = {}
    for r in rows:
        pid = r["p"]["value"].rsplit("/", 1)[1]
        def tp(k):
            x = t(r.get(k))
            if x:
                pr = int(r[k + "p"]["value"]); x["p"] = pr
                if pr < 11: x["d"] = 0
                if pr < 10: x["m"] = 0
            return x
        key = (pid, json.dumps(tp("a")))
        hs[key] = {"p": pid, "zh": (r.get("zh") or {}).get("value"), "en": (r.get("en") or {}).get("value"), "from": tp("a"), "to": tp("b")}
    if oid in YEAR_MAX:
        hs = {k: h for k, h in hs.items() if h["from"] and h["from"]["y"] < YEAR_MAX[oid]}
    out["offices"].append({"id": oid, "zh": zh, "juris": juris, "note": note, "src": f"https://www.wikidata.org/wiki/{oid}",
                           "holders": sorted(hs.values(), key=lambda h: (h["from"] or {"y": 9999})["y"])})
    print(oid, zh, len(hs), "dated", sum(1 for h in hs.values() if h["from"]))
    time.sleep(65)
json.dump(out, open("data/curated/extra_offices.json", "w"), ensure_ascii=False, indent=1)
