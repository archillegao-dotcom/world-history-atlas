"""
中国年号表 → data/china_eras.json.gz
来源：英文维基百科「List of Chinese era names」（按君主分组的年号、起止年；本地副本 data/refs/china/en_List_of_Chinese_era_names.wiki），
君主条目经维基 API 解析为 Wikidata QID，中文名与本名（P1477 出生时姓名 / P1559 本地语言名称）取自 Wikidata，转简体。
输出：{"eras": [{dyn, ruler_qid, ruler_en, ruler_zh, ruler_name, reign, era_zh, era_py, from_y, to_y, note}], "rulers": {qid: {zh, name}}, "src": …}
年份为历史纪年（公元前 1 年 = -1，没有 0 年）。
"""
import json, re, sys, gzip, urllib.request, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "dev")); sys.path.insert(0, str(ROOT / "tools"))
from wpq import qids
from wdsparql import simplifier
t2s = simplifier()
W = (ROOT / "data/refs/china/en_List_of_Chinese_era_names.wiki").read_text()
SRC = "https://en.wikipedia.org/wiki/List_of_Chinese_era_names"


def yr(s, bce):
    s = s.strip()
    v = int(s)
    return -v if bce else v


def period(p):
    p = re.sub(r"<ref.*?(</ref>|/>)", "", p)
    p = re.sub(r"\{\{.*?\}\}", "", p).replace("&ndash;", "–").replace("BC ", "BCE ").strip()
    m = re.match(r"^(\d+)\s*(BCE|BC)?\s*(?:[–-]\s*(\d+)\s*(BCE|BC|CE|AD)?)?\s*(BCE|BC|CE|AD)?", p)
    if not m:
        return None, None
    a, abce, b, bbce, tail = m.groups()
    if b is None:
        bce = bool(abce or (tail in ("BCE", "BC")))
        return yr(a, bce), yr(a, bce)
    bb = bbce in ("BCE", "BC")
    ab = bool(abce) or (bb and not abce and bbce in ("BCE", "BC"))
    return yr(a, ab), yr(b, bb)


eras, cur_dyn, cur_ruler, cur_reign = [], None, None, None
lines = W.split("\n")
i = 0
while i < len(lines):
    L = lines[i]
    m = re.match(r"^===?\s*(.*?)\s*===?\s*$", L)
    if m:
        t = m.group(1)
        lk = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", t)
        cur_dyn = (lk.group(2) or lk.group(1)) if lk else t
        cur_dyn_link = lk.group(1) if lk else None
    m = re.match(r'^!colspan="?\d"?\|(.*)', L)
    if m:
        lk = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", m.group(1))
        cur_ruler = lk.group(1) if lk else re.sub(r"<.*", "", m.group(1)).strip()
        rg = re.search(r"\(r\.\s*([^)]*)\)", m.group(1))
        cur_reign = rg.group(1) if rg else None
    if L.startswith("|") and not L.startswith("|-") and not L.startswith("|}") and "{{lang|zh" in L and cur_ruler:
        py = re.sub(r"<br.*", "", L[1:]).strip().strip("'")
        zh = re.search(r"\{\{lang\|zh[^|]*\|([^}]+)\}\}", L).group(1)
        per = lines[i + 1][1:] if i + 1 < len(lines) else ""
        note = lines[i + 3][1:].strip() if i + 3 < len(lines) and lines[i + 3].startswith("|") and not lines[i + 3].startswith("|-") else ""
        a, b = period(per)
        if a is not None:
            eras.append({"dyn": cur_dyn, "dyn_link": cur_dyn_link, "ruler_en": cur_ruler, "reign": cur_reign, "era_py": py,
                         "era_zh": t2s(zh), "from_y": a, "to_y": b, "period_raw": per.strip(), "note": re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", re.sub(r"\{\{lang\|zh[^|]*\|([^}]+)\}\}", r"\1", note))[:200] or None})
    i += 1
print("eras", len(eras), "rulers", len({e["ruler_en"] for e in eras}))
Q = qids(sorted({e["ruler_en"] for e in eras}))
for t in sorted({e["ruler_en"] for e in eras}):
    if not (Q.get(t) or (None, None))[1]:
        Q.update(qids([t]))
rq = {t: (Q.get(t) or (None, None))[1] for t in {e["ruler_en"] for e in eras}}
# Wikidata：中文标签、本名
ids = sorted({q for q in rq.values() if q})
info = {}
for k in range(0, len(ids), 45):
    u = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids[k:k + 45]), "props": "labels|claims", "languages": "zh-cn|zh-hans|zh|zh-hant", "format": "json"})
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "wha-audit/0.1"})))
    for q, ent in d.get("entities", {}).items():
        lab = next((ent["labels"][l]["value"] for l in ("zh-cn", "zh-hans", "zh", "zh-hant") if l in ent.get("labels", {})), None)
        nm = None
        for p in ("P1477", "P1559"):
            for c in ent.get("claims", {}).get(p, []):
                dv = c["mainsnak"].get("datavalue", {}).get("value", {})
                if isinstance(dv, dict) and dv.get("language", "").startswith("zh") or (isinstance(dv, dict) and dv.get("language") in ("lzh", "zh-hant", "zh-hans")):
                    nm = dv.get("text"); break
            if nm:
                break
        info[q] = {"zh": t2s(lab) if lab else None, "name": t2s(nm) if nm else None}
for e in eras:
    q = rq.get(e["ruler_en"])
    e["ruler_qid"] = q
    e["ruler_zh"] = (info.get(q) or {}).get("zh")
    e["ruler_name"] = (info.get(q) or {}).get("name")
out = {"src": SRC, "eras": eras, "rulers": info}
(ROOT / "data/china_eras.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False).encode()))
miss = sorted({e["ruler_en"] for e in eras if not e["ruler_qid"]})
print("no qid:", len(miss), miss[:20])
print("with personal name:", sum(1 for v in info.values() if v["name"]), "/", len(info))
for e in eras:
    if -10 <= e["from_y"] <= 10:
        print(e)

# ---- 本名补充：中文维基百科条目首句「{君主名}{本名}（…」的模式（只接受紧跟在条目标题后的 2–4 个汉字） ----
def wd_sitelinks(ids):
    out = {}
    for k in range(0, len(ids), 45):
        u = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids[k:k + 45]), "props": "sitelinks", "sitefilter": "zhwiki", "format": "json"})
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "wha-audit/0.1"})))
        for q, ent in d.get("entities", {}).items():
            sl = ent.get("sitelinks", {}).get("zhwiki")
            if sl:
                out[q] = sl["title"]
    return out


sl = wd_sitelinks(ids)
title2q = {v: k for k, v in sl.items()}
titles = list(title2q)
got = 0
def extracts(batch):
    res, cont = {}, {}
    while True:
        u = "https://zh.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": "max",
                                                                           "titles": "|".join(batch), "format": "json", **cont})
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "wha-audit/0.1"})))
        for pg in d["query"]["pages"].values():
            if pg.get("extract"):
                res[pg["title"]] = pg["extract"]
        if "continue" not in d:
            return res
        cont = d["continue"]


era_names = {e["era_zh"] for e in eras}
for k in range(0, len(titles), 10):
    for title, ex in extracts(titles[k:k + 10]).items():
        q = title2q.get(title)
        if not q:
            continue
        ex = t2s(ex.strip())
        for lab in {t2s(title), info.get(q, {}).get("zh") or ""}:
            if lab and ex.startswith(lab):
                m = re.match(r"^([\u4e00-\u9fff]{2,4})[（(]", ex[len(lab):])
                if m and m.group(1) != lab:
                    info.setdefault(q, {})["name"] = m.group(1)
                    info[q]["name_src"] = "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(title)
                    got += 1
                    break
# Wikidata P1477/P1559 的值若等于君主名或是年号（如「明神宗 → 万历」），视为无效
for q, v in info.items():
    if v.get("name") and not v.get("name_src") and (v["name"] == v.get("zh") or v["name"] in era_names):
        v["name"] = None
for e in eras:
    e["ruler_name"] = (info.get(e["ruler_qid"]) or {}).get("name")
out = {"src": SRC, "eras": eras, "rulers": info}
(ROOT / "data/china_eras.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False).encode()))
print("zhwiki personal names added:", got, "total with name:", sum(1 for v in info.values() if v.get("name")), "/", len(info))
print([(v["zh"], v.get("name")) for q, v in list(info.items())[:30]])
