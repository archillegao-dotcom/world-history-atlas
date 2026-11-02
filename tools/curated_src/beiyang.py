"""北洋政府（1912–1928）大总统与国务总理任期：解析英文维基「List of presidents of the Republic of China」「List of premiers of the Republic of China」
的 Timeline（data/refs/wiki/en_list_*_roc.wiki），人物 QID/中文名由维基 API 与 Wikidata 标签取得 → 写入 data/curated/extra_offices.json 的
Q887003（大总统）/Q702650（国务总理）两个职位（管辖 1912–1949 的中华民国 Q13426199），只取 1928-06-04 以前开始的任期。"""
import json, re, urllib.parse, urllib.request
UA = {"User-Agent": "WHA-audit/0.6.1"}
from opencc import OpenCC
_cc = OpenCC("t2s")
_s = lambda x: _cc.convert(x) if x else x
def parse(fn):
    out, cur = [], []
    for line in open(fn, encoding="utf-8"):
        m = re.match(r"\s*from:\s*(\d\d)/(\d\d)/(\d{4})\s*till:\s*(\d\d)/(\d\d)/(\d{4})", line)
        if m:
            d1, m1, y1, d2, m2, y2 = map(int, m.groups())
            cur.append(({"y": y1, "m": m1, "d": d1, "p": 11}, {"y": y2, "m": m2, "d": d2, "p": 11}))
            t = re.search(r'text:"\[\[([^\]|]+)', line)
            if t:
                out += [(t.group(1), a, b) for a, b in cur]; cur = []
        elif re.match(r"\s*bar:", line) and not re.match(r"\s*bar:\w+\s*$", line) is None:
            pass
    return out
def qids(titles):
    r = {}
    for i in range(0, len(titles), 40):
        u = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item", "redirects": 1, "format": "json", "titles": "|".join(titles[i:i+40])})
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA)))["query"]
        norm = {x["to"]: x["from"] for x in d.get("redirects", []) + d.get("normalized", [])}
        for p in d["pages"].values():
            t = p["title"]; r[norm.get(t, t)] = p.get("pageprops", {}).get("wikibase_item"); r[t] = r[norm.get(t, t)]
    return r
def zh(ids):
    r = {}
    for i in range(0, len(ids), 45):
        u = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids[i:i+45]), "props": "labels", "languages": "zh-cn|zh-hans|zh", "format": "json"})
        for k, v in json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA)))["entities"].items():
            L = v.get("labels", {}); r[k] = _s(next((L[l]["value"] for l in ("zh-cn", "zh-hans", "zh") if l in L), None))
    return r
X = json.load(open("data/curated/extra_offices.json"))
for oid, fn, name, note in [("Q887003", "data/refs/wiki/en_list_presidents_roc.wiki", "中华民国大总统（北洋政府）", "北洋政府时期的中华民国大总统（含代理、临时执政、陆海军大元帅）"),
                            ("Q702650", "data/refs/wiki/en_list_premiers_roc.wiki", "国务总理（北洋政府）", "北洋政府时期的国务总理（1914–1916 年为国务卿；含代理）")]:
    rows = [r for r in parse(fn) if (r[1]["y"], r[1]["m"], r[1]["d"]) < (1928, 6, 4)]
    q = qids(sorted({r[0] for r in rows})); z = zh(sorted({v for v in q.values() if v}))
    hs = [{"p": q[t], "zh": z.get(q[t]), "en": t.split("(")[0].strip(), "from": a, "to": b} for t, a, b in rows if q.get(t)]
    print(oid, len(rows), "rows", len(hs), "with QID", [h["zh"] for h in hs])
    X["offices"] = [o for o in X["offices"] if o["id"] != oid] + [{"id": oid, "zh": name, "juris": ["Q13426199"], "note": note,
        "src": "https://en.wikipedia.org/wiki/" + fn.split("en_")[1].replace(".wiki", "").replace("list", "List"), "holders": hs}]
json.dump(X, open("data/curated/extra_offices.json", "w"), ensure_ascii=False, indent=1)
