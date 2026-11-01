#!/usr/bin/env python3
"""
为地图上的政权名称（historical-basemaps 的英文 NAME）查找中文名，输出 data/polity_names.json。
方法：把 NAME 当作英文维基百科条目标题，经 Wikidata wbgetentities(sites=enwiki) 解析到实体，
只有当该实体看起来确实是「政权/国家/民族/文化」（P31 在白名单中，或有 P576 解散日期）时才采用其中文标签，
避免把「Georgia」之类误译成城市或美国州。找不到就保持英文原名——宁缺毋滥。
结果同时记录 QID，供以后按 QID 精确匹配国家/国籍。
"""
import gzip, json, os, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WHA_DATA_DIR", ROOT / "data"))
UA = "WorldHistoryAtlas/0.1 (offline educational history atlas) python-requests"
OK_TYPES = {
    "Q6256", "Q3024240", "Q7275", "Q417175", "Q48349", "Q1250464", "Q3624078", "Q1763527", "Q15634554",
    "Q41710", "Q133311", "Q2472587", "Q465299", "Q1520223", "Q164142", "Q208500", "Q4204501", "Q20181813",
    "Q1371288", "Q1307214", "Q112099", "Q185145", "Q10711424", "Q12759805", "Q107390", "Q160016",
    "Q28171280", "Q1145276", "Q3591867", "Q50068795", "Q11514315", "Q2577883", "Q209166", "Q12560",
    "Q849866", "Q15642541", "Q1048835", "Q170156", "Q1637706", "Q5255892", "Q1072968", "Q3918",
}


def main():
    names = set()
    for f in (DATA / "basemaps").glob("*.geojson.gz"):
        for ft in json.loads(gzip.decompress(f.read_bytes()))["features"]:
            if ft["properties"].get("NAME"):
                names.add(ft["properties"]["NAME"])
    out_f = DATA / "polity_names.json"
    out = json.loads(out_f.read_text(encoding="utf-8")) if out_f.exists() else {}
    todo = sorted(n for n in names if n not in out)
    print(len(names), "names,", len(todo), "to look up")
    for k in range(0, len(todo), 50):
        chunk = todo[k:k + 50]
        r = requests.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities", "sites": "enwiki", "titles": "|".join(chunk),
            "props": "labels|claims|sitelinks", "languages": "zh-cn|zh-hans|zh|en", "format": "json"},
            headers={"User-Agent": UA}, timeout=60)
        r.raise_for_status()
        js = r.json()
        if "error" in js:
            raise RuntimeError(js["error"])
        # 标题规范化与重定向映射：输入名 -> 实际标题
        norm = {x["from"]: x["to"] for x in js.get("normalized", [])}
        by_title = {}
        for q, e in js.get("entities", {}).items():
            t = e.get("sitelinks", {}).get("enwiki", {}).get("title")
            if t:
                by_title[t] = (q, e)
        for n in chunk:
            hit = by_title.get(norm.get(n, n))
            rec = {"qid": None, "zh": None}
            if hit:
                q, e = hit
                p31 = {c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P31", [])}
                if p31 & OK_TYPES or "P576" in e.get("claims", {}):
                    labels = e.get("labels", {})
                    zh = next((labels[x]["value"] for x in ("zh-cn", "zh-hans", "zh") if x in labels), None)
                    if zh:
                        try:
                            from opencc import OpenCC
                            zh = OpenCC("t2s").convert(zh)
                        except ImportError:
                            pass
                    rec = {"qid": q, "zh": zh}
            out[n] = rec
        time.sleep(0.5)
    # 第二轮：标题不是精确条目名的，经英文维基 API 跟随重定向/规范化取得 QID，再做同样的类型检查
    todo = sorted(n for n, rec in out.items() if not rec.get("zh"))
    print("second pass via enwiki redirects:", len(todo))
    for k in range(0, len(todo), 50):
        chunk = todo[k:k + 50]
        r = requests.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "titles": "|".join(chunk), "redirects": 1, "prop": "pageprops",
            "ppprop": "wikibase_item", "format": "json", "formatversion": 2}, headers={"User-Agent": UA}, timeout=60)
        js = r.json().get("query", {})
        hop = {x["from"]: x["to"] for x in js.get("normalized", []) + js.get("redirects", [])}
        qmap = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in js.get("pages", [])}
        name_q = {}
        for n in chunk:
            t = n
            for _ in range(3):
                t = hop.get(t, t)
            if qmap.get(t):
                name_q[n] = qmap[t]
        ids = sorted(set(name_q.values()))
        if ids:
            r2 = requests.get("https://www.wikidata.org/w/api.php", params={
                "action": "wbgetentities", "ids": "|".join(ids), "props": "labels|claims",
                "languages": "zh-cn|zh-hans|zh|en", "format": "json"}, headers={"User-Agent": UA}, timeout=60)
            ents = r2.json().get("entities", {})
            for n, q in name_q.items():
                e = ents.get(q, {})
                p31 = {c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P31", [])}
                if p31 & OK_TYPES or "P576" in e.get("claims", {}):
                    labels = e.get("labels", {})
                    zh = next((labels[x]["value"] for x in ("zh-cn", "zh-hans", "zh") if x in labels), None)
                    if zh:
                        try:
                            from opencc import OpenCC
                            zh = OpenCC("t2s").convert(zh)
                        except ImportError:
                            pass
                        out[n] = {"qid": q, "zh": zh, "via": "redirect"}
        time.sleep(0.5)
    out_f.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print("with zh:", sum(1 for v in out.values() if v.get("zh")), "/", len(out))


if __name__ == "__main__":
    main()
