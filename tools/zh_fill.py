"""补中文名（任务 C，v0.6.1）：显示名没有汉字的条目，按以下顺序找中文名，找到即记录来源：
  1. Wikidata 中文标签（zh-cn → zh-hans → zh-sg → zh-my → zh → zh-tw → zh-hk → zh-mo → zh-hant；繁体转简体）
  2. 中文维基百科条目名（Wikidata sitelink zhwiki，去掉消歧义括号，繁转简）
  3. 底图名称（historical-basemaps，没有 QID）：英文维基同名条目的中文维基语言链接
找不到的不翻译（显示原名并标「暂无通用译名」），由 tools/accept/zh_coverage.py 计数。
输出：data/curated/zh_labels.json（QID → {zh, src}）、data/curated/zh_basemap_names.json（底图名 → {zh, src, title}）
用法：.venv/bin/python tools/zh_fill.py [--only-basemap]"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, ".")
from opencc import OpenCC
from backend.datafile import read_json
cc = OpenCC("t2s"); CJK = re.compile(r"[\u4e00-\u9fff]")
UA = {"User-Agent": "WorldHistoryAtlas/0.6.1 (non-commercial; zh label fill)"}
D = Path("data")
def get(u):
    for k in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception as e:
            time.sleep(3 * (k + 1)); err = e
    print("FAIL", u[:120], err); return {}
def need_qids():
    q = set()
    def chk(lst, name_f=("zh",)):
        for r in lst or []:
            if isinstance(r, dict) and r.get("id", "").startswith("Q") and not any(CJK.search(r.get(f) or "") for f in name_f):
                q.add(r["id"])
    for f in ["states", "persons", "ruler_persons", "offices", "orgs", "cities", "treaties", "alliances"]:
        chk(read_json(D / f"{f}.json.gz", []))
    for f in ["events", "people_politician", "people_writer", "people_philosopher"]:
        chk(read_json(D / f"{f}.json.gz", []), ("name",))
    rs = json.loads((D / "curated/runtime_states.json").read_text())
    q |= {k for k, v in rs.items() if k.startswith("Q") and not CJK.search(v.get("zh") or "")}
    xo = json.loads((D / "curated/extra_offices.json").read_text())
    q |= {h["p"] for o in xo["offices"] for h in o["holders"] if not CJK.search(h.get("zh") or "")}
    return sorted(q)
LANGS = ["zh-cn", "zh-hans", "zh-sg", "zh-my", "zh", "zh-tw", "zh-hk", "zh-mo", "zh-hant"]
def clean(t):
    return cc.convert(re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", t)).strip()
def by_qid(qs, out):
    for i in range(0, len(qs), 50):
        ids = [q for q in qs[i:i + 50] if q not in out]
        if not ids:
            continue
        d = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids), "props": "labels|sitelinks",
                "languages": "|".join(LANGS), "sitefilter": "zhwiki", "format": "json"}))
        for k, v in (d.get("entities") or {}).items():
            L = v.get("labels", {})
            lab = next(((l, L[l]["value"]) for l in LANGS if l in L and CJK.search(L[l]["value"])), None)
            if lab:
                out[k] = {"zh": cc.convert(lab[1]), "src": f"Wikidata 中文标签（{lab[0]}）"}
            elif "zhwiki" in v.get("sitelinks", {}):
                out[k] = {"zh": clean(v["sitelinks"]["zhwiki"]["title"]), "src": "中文维基百科条目名"}
            else:
                out[k] = None
        if i % 2000 == 0:
            print(i, len(qs), sum(1 for x in out.values() if x)); sys.stdout.flush()
        time.sleep(0.3)
def basemap(out):
    names = json.loads((D / "polity_names.json").read_text())
    todo = [n for n, v in names.items() if n.strip() and not v.get("zh") and n not in out]
    print("basemap names", len(todo))
    for i in range(0, len(todo), 40):
        ch = todo[i:i + 40]
        d = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "langlinks", "lllang": "zh", "redirects": 1,
                "titles": "|".join(ch), "format": "json", "lllimit": "max"}))
        q = d.get("query", {}); m = {}
        for x in q.get("normalized", []) + q.get("redirects", []):
            m[x["to"]] = m.get(x["from"], x["from"])
        found = {}
        for p in q.get("pages", {}).values():
            orig = m.get(p["title"], p["title"]); orig = m.get(orig, orig)
            ll = p.get("langlinks")
            if ll:
                found[orig] = {"zh": clean(ll[0]["*"]), "src": "英文维基同名条目的中文维基链接", "title": p["title"]}
        for n in ch:
            out[n] = found.get(n)
        time.sleep(0.3)
if __name__ == "__main__":
    pq = D / "curated/zh_labels.json"; pb = D / "curated/zh_basemap_names.json"
    lab = json.loads(pq.read_text())["labels"] if pq.exists() else {}
    bm = json.loads(pb.read_text())["names"] if pb.exists() else {}
    if "--only-basemap" not in sys.argv:
        qs = need_qids(); print("qids needing zh", len(qs))
        by_qid(qs, lab)
        pq.write_text(json.dumps({"_doc": __doc__, "labels": lab}, ensure_ascii=False, indent=0))
    basemap(bm)
    pb.write_text(json.dumps({"_doc": __doc__, "names": bm}, ensure_ascii=False, indent=0))
    print("DONE qid found", sum(1 for x in lab.values() if x), "/", len(lab), "basemap found", sum(1 for x in bm.values() if x), "/", len(bm))
