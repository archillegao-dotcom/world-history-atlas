"""第 2 步：对第 1 步仍有空月份的空档，用 Wikidata 反查（CirrusSearch haswbstatement:P39=职位）该职位全部任职者，
找出任期与空档重叠、但本地数据没有的人（含 P1365/P1366 前后任链）。→ logs/gap_verify_step2.json"""
import json, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from backend import config
from backend.polity import PolityResolver
UA = {"User-Agent": "WorldHistoryAtlas/0.6.1 (research; box)"}
def get(u):
    for k in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception:
            time.sleep(4 * (k + 1))
    return {}
def tval(sn):
    v = (sn.get("datavalue") or {}).get("value")
    if not v: return None
    t = v["time"]; p = v["precision"]
    sign = -1 if t[0] == "-" else 1
    y, m, d = t[1:].split("T")[0].split("-")
    return {"y": sign * int(y), "m": int(m) if p >= 10 else 0, "d": int(d) if p >= 11 else 0, "p": p}
def key(t, end=False):
    if not t: return None
    y = t["y"]; m = t["m"] or (12 if end else 1); d = t["d"] or (28 if end else 1)
    return y + (m - 1) / 12 + (d - 1) / 365
cache = {}
def holders_of(pos):
    if pos in cache: return cache[pos]
    r = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": f"haswbstatement:P39={pos}", "srlimit": 500, "format": "json"}))
    qs = [x["title"] for x in r.get("query", {}).get("search", [])]
    out = []
    for i in range(0, len(qs), 50):
        e = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(qs[i:i+50]), "props": "claims|labels|sitelinks", "languages": "zh|zh-hans|zh-cn|en", "sitefilter": "enwiki|zhwiki", "format": "json"}))
        for q, ent in e.get("entities", {}).items():
            L = ent.get("labels", {})
            for c in ent.get("claims", {}).get("P39", []):
                if (c["mainsnak"].get("datavalue") or {}).get("value", {}).get("id") != pos: continue
                qu = c.get("qualifiers", {})
                f = tval(qu["P580"][0]) if "P580" in qu else None
                t = tval(qu["P582"][0]) if "P582" in qu else None
                rep = [x["datavalue"]["value"]["id"] for x in qu.get("P1365", []) if x.get("datavalue")]
                by = [x["datavalue"]["value"]["id"] for x in qu.get("P1366", []) if x.get("datavalue")]
                juris = [x["datavalue"]["value"]["id"] for x in qu.get("P1001", []) if x.get("datavalue")]
                out.append({"p": q, "en": (L.get("en") or {}).get("value"), "zh": next((L[k]["value"] for k in ("zh-hans", "zh-cn", "zh") if k in L), None),
                            "enwiki": (ent.get("sitelinks", {}).get("enwiki") or {}).get("title"), "from": f, "to": t, "replaces": rep, "replaced_by": by, "juris": juris})
        time.sleep(0.5)
    cache[pos] = out
    return out
def main():
    R = PolityResolver(config.DATA_DIR)
    s1 = json.load(open("logs/gap_verify_step1.json"))
    open_ = [g for g in s1 if not g["cls"]]
    res = []
    for g in open_:
        offs = [o for o in R.office_by_state.get(g["state"], []) if (o.get("zh") or o.get("en")) == g["office"] or o.get("en") == g["office"]]
        have = {h["p"] for o in offs for h in o.get("holders", [])}
        poss = sorted({o.get("pos") or o["id"].split("@")[0] for o in offs})
        cands = []
        for pos in poss:
            for h in holders_of(pos):
                a, b = key(h["from"]), key(h["to"], True)
                if a is None and b is None: continue
                for lo, hi in g["empty_spans"]:
                    if (a is None or a < hi) and (b is None or b > lo) and (a is not None or b is not None):
                        if h["p"] not in have:
                            cands.append({**h, "pos": pos, "span": [lo, hi]})
                        break
        res.append({**g, "poss": poss, "offices": [o["id"] for o in offs], "wd_candidates": cands})
        print(g["state_zh"], g["office"], g["empty_spans"][:2], "→", [(c["zh"] or c["en"], c["from"] and c["from"]["y"], c["to"] and c["to"]["y"], c["juris"][:2]) for c in cands][:6], flush=True)
    json.dump(res, open("logs/gap_verify_step2.json", "w"), ensure_ascii=False, indent=0)
    print("DONE", sum(1 for r in res if r["wd_candidates"]), "of", len(res), "have candidates")
if __name__ == "__main__":
    main()
