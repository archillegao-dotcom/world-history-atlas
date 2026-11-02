#!/usr/bin/env python3
"""
补充政权条目：整理数据（二战按月边界/战线、实际控制区、CShapes 分期、补充小国）引用了、但 data/states.json.gz 里没有的 Wikidata 条目
（多为占领当局、傀儡政权、军事管理区，不属于 build_states.py 抓取的「国家/政权」类）。
从 Wikidata API 取标签（zh/en）、描述、P571/P576、P41（国旗）、P36（首都）→ data/curated/runtime_states.json（运行时由 PolityResolver 读入）。
用法：.venv/bin/python tools/build_runtime_states.py
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "WorldHistoryAtlas/0.8 (non-commercial research; runtime_states)"}


def refs():
    q = set()
    txt = (DATA / "curated" / "war_fronts_hist.json").read_text(encoding="utf-8") + (DATA / "curated" / "control_zones.json").read_text(encoding="utf-8") + \
        (DATA / "curated" / "cshapes_periods.json").read_text(encoding="utf-8") + \
        ((DATA / "curated" / "name_candidates.json").read_text(encoding="utf-8") if (DATA / "curated" / "name_candidates.json").exists() else "")
    q |= set(re.findall(r'"(Q\d+)"', txt))
    d = json.loads(gzip.decompress((DATA / "cshapes.json.gz").read_bytes()))
    q |= {e["qid"] for e in d["extras"]}
    return q


def wd_time(c):
    try:
        v = c[0]["mainsnak"]["datavalue"]["value"]
        t, p = v["time"], v["precision"]
        m = re.match(r"([+-]\d+)-(\d\d)-(\d\d)", t)
        y, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return {"y": y, "m": mo if p >= 10 else 0, "d": dd if p >= 11 else 0, "p": p}
    except Exception:
        return None


def main():
    states = {s["id"] for s in json.loads(gzip.decompress((DATA / "states.json.gz").read_bytes()))}
    need = sorted(q for q in refs() if q not in states)
    print("missing", len(need), need)
    out_p = DATA / "curated" / "runtime_states.json"
    old = json.loads(out_p.read_text(encoding="utf-8")) if out_p.exists() else {}
    out = {"_doc": __doc__.strip().splitlines()}
    for i in range(0, len(need), 40):
        ids = need[i:i + 40]
        u = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids), "props": "labels|descriptions|claims|sitelinks",
                                                                             "languages": "zh-cn|zh-hans|zh|en", "format": "json"})
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        for q, e in d.get("entities", {}).items():
            if "missing" in e:
                continue
            L = e.get("labels", {})
            zh = next((L[k]["value"] for k in ("zh-cn", "zh-hans", "zh") if k in L), None)
            if zh:   # Wikidata 的 zh 标签常是繁体：统一转简体（v0.6.1）
                import opencc
                zh = opencc.OpenCC("t2s").convert(zh)
            en = L.get("en", {}).get("value")
            D = e.get("descriptions", {})
            c = e.get("claims", {})
            flag = None
            if "P41" in c:
                try:
                    flag = "http://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(c["P41"][0]["mainsnak"]["datavalue"]["value"])
                except Exception:
                    pass
            sl = e.get("sitelinks", {})
            out[q] = {"id": q, "zh": zh, "en": en, "desc": next((D[k]["value"] for k in ("zh-cn", "zh-hans", "zh") if k in D), None), "desc_en": D.get("en", {}).get("value"),
                      "from": wd_time(c.get("P571")) or wd_time(c.get("P580")), "to": wd_time(c.get("P576")) or wd_time(c.get("P582")),
                      "flag": flag, "enwiki": sl.get("enwiki", {}).get("title"), "zhwiki": sl.get("zhwiki", {}).get("title"),
                      "sources": [f"https://www.wikidata.org/wiki/{q}"], "runtime": True}
        time.sleep(0.5)
    for q, r in old.items():
        if q.startswith("Q") and q not in out and q in need:
            out[q] = r
    out_p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", len(out) - 1)
    for q in need:
        r = out.get(q)
        print(q, r and r["zh"], r and r["en"], r and r["from"], r and r["to"])


if __name__ == "__main__":
    main()
