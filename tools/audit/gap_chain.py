"""第 3 步：用 Wikidata 前后任链（P39 限定符 P1365 前任 / P1366 继任）找空档里缺的君主。
空档前最后一位任职者的「继任者」、空档后第一位任职者的「前任」——若不在本地数据里，就是缺失的君主候选（a 类），
取其 P39 该职位的起止时间；没有时取出生/去世年份供人工核对。→ logs/gap_verify_step3.json"""
import json, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from backend import config
from backend.polity import PolityResolver
sys.path.insert(0, "tools/audit")
from gap_wd import get, tval, key  # noqa
R = PolityResolver(config.DATA_DIR)
s2 = json.load(open("logs/gap_verify_step2.json"))
API = "https://www.wikidata.org/w/api.php?"
ENT = {}
def ents(ids):
    ids = [i for i in ids if i not in ENT]
    for i in range(0, len(ids), 50):
        e = get(API + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids[i:i+50]), "props": "claims|labels|sitelinks", "languages": "zh|zh-hans|zh-cn|en", "sitefilter": "enwiki|zhwiki", "format": "json"}))
        ENT.update(e.get("entities", {}))
        time.sleep(0.3)
def ids_of(claims, p):
    return [x["datavalue"]["value"]["id"] for x in claims.get(p, []) if x.get("datavalue")]
def p39(q, pos):
    return [c for c in ENT.get(q, {}).get("claims", {}).get("P39", []) if (c["mainsnak"].get("datavalue") or {}).get("value", {}).get("id") == pos]
def lab(q):
    L = ENT.get(q, {}).get("labels", {})
    return next((L[k]["value"] for k in ("zh-hans", "zh-cn", "zh", "en") if k in L), q)
def hk(t, end=False):
    return key(t, end) if t else None
out = []
for g in s2:
    if not g["empty_spans"]:
        continue
    offs = [o for o in R.office_by_state.get(g["state"], []) if o["id"] in g["offices"]]
    hs = [h for o in offs for h in o.get("holders", [])]
    have = {h["p"] for h in hs}
    found = []
    for lo, hi in g["empty_spans"]:
        prev = max((h for h in hs if hk(h.get("to"), True) is not None and hk(h.get("to"), True) <= lo + 0.2), key=lambda h: hk(h["to"], True), default=None)
        nxt = min((h for h in hs if hk(h.get("from")) is not None and hk(h.get("from")) >= hi - 0.2), key=lambda h: hk(h["from"]), default=None)
        ents([x["p"] for x in (prev, nxt) if x])
        cand = set()
        for pos in g["poss"]:
            if prev:
                for c in p39(prev["p"], pos): cand |= set(ids_of(c.get("qualifiers", {}), "P1366"))
            if nxt:
                for c in p39(nxt["p"], pos): cand |= set(ids_of(c.get("qualifiers", {}), "P1365"))
        cand -= have
        ents(list(cand))
        for x in cand:
            cl = ENT.get(x, {}).get("claims", {})
            st = []
            for pos in g["poss"]:
                for c in p39(x, pos):
                    qu = c.get("qualifiers", {})
                    st.append({"pos": pos, "from": tval(qu["P580"][0]) if "P580" in qu else None, "to": tval(qu["P582"][0]) if "P582" in qu else None,
                               "replaces": ids_of(qu, "P1365"), "replaced_by": ids_of(qu, "P1366")})
            found.append({"span": [lo, hi], "p": x, "label": lab(x), "enwiki": (ENT.get(x, {}).get("sitelinks", {}).get("enwiki") or {}).get("title"),
                          "p31": ids_of(cl, "P31")[:3], "born": tval(cl["P569"][0]["mainsnak"]) if "P569" in cl else None,
                          "died": tval(cl["P570"][0]["mainsnak"]) if "P570" in cl else None, "p39": st,
                          "prev": prev and prev["p"], "next": nxt and nxt["p"]})
    out.append({**g, "chain": found})
    print(g["state_zh"], "|", g["office"], g["empty_spans"][:3], "→", [(f["label"], f["span"], [(s["from"] and s["from"]["y"], s["to"] and s["to"]["y"]) for s in f["p39"]], f["died"] and f["died"]["y"]) for f in found], flush=True)
json.dump(out, open("logs/gap_verify_step3.json", "w"), ensure_ascii=False, indent=0)
print("DONE", sum(1 for g in out if g["chain"]), "of", len(out))
