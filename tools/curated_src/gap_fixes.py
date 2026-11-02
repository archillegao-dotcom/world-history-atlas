"""v0.6.1 君主空档核对：解析并核对 gap_data.py / interregna_gaps.py 里的人物（wbgetentities），
把类别 a 的任职记录写入 data/curated/extra_offices.json 的 extra_holders（带 "gap_fix": true，可重复运行）。
用法：.venv/bin/python tools/curated_src/gap_fixes.py && python3 tools/curated_src/interregna.py"""
import json, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, "."); sys.path.insert(0, "tools/curated_src")
import gap_data
UA = {"User-Agent": "WorldHistoryAtlas/0.6.1 (research; box)"}
API = "https://www.wikidata.org/w/api.php?"
def get(params):
    for k in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(API + urllib.parse.urlencode({**params, "format": "json"}), headers=UA), timeout=60))
        except Exception:
            time.sleep(4 * (k + 1))
    raise SystemExit("wikidata failed")
src = open("tools/curated_src/interregna_gaps.py", encoding="utf-8").read()
titles = sorted({p["person"] for p in gap_data.A if not re.match(r"^Q\d+$", p["person"])} | set(re.findall(r'"E:([^"]+)"', src)) | set(re.findall(r'D\(\d+, \d+, \d+\), "([^"]+)", "[^"]+", \d+, \d+\)', src)))
qids = sorted({p["person"] for p in gap_data.A if re.match(r"^Q\d+$", p["person"])} | set(re.findall(r'G\("(Q\d+)"', src)))
res, info, bad = {}, {}, []
for i in range(0, len(titles), 50):
    r = get({"action": "wbgetentities", "sites": "enwiki", "titles": "|".join(titles[i:i+50]), "props": "labels|sitelinks|claims", "languages": "zh|zh-hans|zh-cn|en", "sitefilter": "enwiki", "redirects": "yes"})
    for q, e in r.get("entities", {}).items():
        if q.startswith("-") or "missing" in e:
            continue
        t = e["sitelinks"]["enwiki"]["title"]
        info[q] = e
        for want in titles[i:i+50]:
            if want.replace("_", " ") == t or want not in res and want.lower() == t.lower():
                res[want] = q
        res.setdefault(t, q)
    time.sleep(0.5)
# 重定向：用标题再查一次未解析的
for t in [t for t in titles if t not in res]:
    r = get({"action": "query", "titles": t, "redirects": 1, "prop": "pageprops", "ppprop": "wikibase_item"})
    pass
miss = [t for t in titles if t not in res]
for t in miss:
    r = urllib.request.urlopen(urllib.request.Request("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "titles": t, "redirects": 1, "prop": "pageprops", "ppprop": "wikibase_item", "format": "json"}), headers=UA), timeout=60)
    pg = next(iter(json.load(r)["query"]["pages"].values()))
    q = (pg.get("pageprops") or {}).get("wikibase_item")
    if q:
        res[t] = q
    else:
        bad.append(t)
allq = sorted(set(res.values()) | set(qids))
for i in range(0, len(allq), 50):
    r = get({"action": "wbgetentities", "ids": "|".join(allq[i:i+50]), "props": "labels|claims|sitelinks", "languages": "zh|zh-hans|zh-cn|en", "sitefilter": "enwiki|zhwiki"})
    info.update(r.get("entities", {}))
    time.sleep(0.4)
def lab(q, langs=("zh-hans", "zh-cn", "zh", "en")):
    L = info.get(q, {}).get("labels", {})
    return next((L[k]["value"] for k in langs if k in L), None)
chk = {}
for q in allq:
    e = info.get(q, {})
    p31 = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P31", [])]
    chk[q] = {"en": lab(q, ("en",)), "zh": lab(q), "human": "Q5" in p31, "enwiki": (e.get("sitelinks", {}).get("enwiki") or {}).get("title")}
nonhuman = [q for q, c in chk.items() if not c["human"]]
json.dump({"_doc": "gap_fixes.py 解析的英文维基条目 → QID（wbgetentities 核对：存在、P31=Q5 人类、标签）", "qids": res, "check": chk},
          open("data/curated/gap_qids.json", "w"), ensure_ascii=False, indent=0)
print("titles", len(titles), "resolved", len(res), "unresolved", bad, "non-human", [(q, chk[q]["en"]) for q in nonhuman])
# 写 extra_holders
from backend import config
from backend.polity import PolityResolver
R = PolityResolver(config.DATA_DIR)
xo = json.load(open("data/curated/extra_offices.json"))
xo["extra_holders"] = [h for h in xo.get("extra_holders", []) if not h.get("gap_fix")]
s1 = {g["state"]: g for g in json.load(open("logs/gap_verify_step2.json"))}
nf = []
for a in gap_data.A:
    q = a["person"] if re.match(r"^Q\d+$", a["person"]) else res.get(a["person"])
    if not q:
        nf.append(("person", a["person"])); continue
    offs = R.office_by_state.get(a["state"], [])
    o = next((o for o in offs if a["office"].lower() in (o.get("en") or "").lower() and not re.search(r"(?i)consort|heir|crown", o.get("en") or "")), None)
    if o is None and a["state"] in s1 and s1[a["state"]]["offices"]:
        o = next((x for x in offs if x["id"] == s1[a["state"]]["offices"][0]), None)
    if o is None:
        nf.append(("office", a["state"], a["office"])); continue
    xo["extra_holders"].append({"office": o["id"], "p": q, "zh": chk[q]["zh"], "en": chk[q]["en"], "from": {**a["from"], "p": 11 if a["from"]["d"] else 10 if a["from"]["m"] else 9},
                                "to": ({**a["to"], "p": 11 if a["to"]["d"] else 10 if a["to"]["m"] else 9} if a["to"] else None),
                                "note": "v0.6.1 君主空档核对补入（Wikidata 缺此任职记录或缺起止时间）" + ("：" + a["note"] if a["note"] else ""), "src": a["src"], "gap_fix": True})
json.dump(xo, open("data/curated/extra_offices.json", "w"), ensure_ascii=False, indent=1)
print("extra holders", sum(1 for h in xo["extra_holders"] if h.get("gap_fix")), "not found", nf)
