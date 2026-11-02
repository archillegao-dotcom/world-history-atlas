"""补中文名第 4 步（v0.6.1）：Wikidata 项本身没有中文标签/中文维基链接的政权、城市、职位，
取其英文维基条目的中文语言链接（中文维基可能把同一主题挂在另一个 Wikidata 项上）。消歧义页跳过。结果并入 data/curated/zh_labels.json。"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
UA = {"User-Agent": "WorldHistoryAtlas/0.6.1 (research; box)"}
def get(u):
    for k in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception: time.sleep(3 * (k + 1))
    return {}
import opencc; cc = opencc.OpenCC("t2s")
miss = json.load(open(sys.argv[1]))
P = Path("data/curated/zh_labels.json"); d = json.loads(P.read_text()); lab = d["labels"]
todo = {}
for kind, q, en, ew in miss:
    if ew:
        t = urllib.parse.unquote(ew.rsplit("/wiki/", 1)[-1]).replace("_", " ")
        todo[t] = q
tl = list(todo); n = 0
for i in range(0, len(tl), 40):
    r = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "langlinks|pageprops", "lllang": "zh", "ppprop": "disambiguation", "redirects": 1, "titles": "|".join(tl[i:i+40]), "format": "json"}))
    q = r.get("query", {}); m = {}
    for x in q.get("normalized", []) + q.get("redirects", []):
        m[x["to"]] = m.get(x["from"], x["from"])
    for p in q.get("pages", {}).values():
        orig = m.get(p["title"], p["title"]); orig = m.get(orig, orig)
        ll = p.get("langlinks")
        if ll and "disambiguation" not in p.get("pageprops", {}) and orig in todo:
            z = cc.convert(re.sub(r"\s*[（(][^）)]*[）)]$", "", ll[0]["*"]))
            if re.search(r"[\u4e00-\u9fff]", z):
                lab[todo[orig]] = {"zh": z, "src": f"英文维基条目「{orig}」的中文维基链接"}; n += 1
                print(todo[orig], orig, "→", z)
    time.sleep(0.3)
P.write_text(json.dumps(d, ensure_ascii=False, indent=0)); print("added", n, "of", len(todo))
