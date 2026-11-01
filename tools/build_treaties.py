#!/usr/bin/env python3
"""
条约数据（「国家精神」）构建：Wikidata 中 treaty（Q131569）及其所有子类（和约、同盟条约、贸易协定、边界条约……）。

收录条件：至少 2 个语言版本的维基条目，或有签署方（P1891）。
字段：中英文名、简介、类型（P31）、签订日期（P585 时间点；没有时用 P580 开始时间 / P571 成立时间）、
生效日期（P7588）、终止（P582 结束时间 / P576 废止）、签署方 P1891 与参与方 P710（只保留能对应到
data/states.json.gz 中政权的；其他签署方如个人只计数）、维基百科与维基文库条目、全文链接 P953。

另外把条约「喂给」阵营地图（data/alliances.json.gz 追加，source = "treaty"）：
  a) Wikidata 中的同盟条目（military alliance 等）自身没有 ≥2 个成员、但与某条约互相引用
     （同盟条目的任一属性指向该条约，或反之）时，用条约的签署方作为成员，条约日期作为加入时间；
     例：英葡同盟（Q2838032）← 1373 年英葡条约（Q1150265）。
  b) 类型名称中含 alliance 的条约（同盟条约、防御同盟……），本身有 ≥2 个政权签署方。
需要先运行 build_states.py。
"""
from __future__ import annotations

import collections
import gzip
import json
import re

from build_states import ALLIANCE_ROOTS, labels_for, q
from wdsparql import DATA, cached, parse_point, parse_time, pick_zh, qid, simplifier, v, write_gz

t2s = simplifier()
TREATY = "wd:Q131569"
BATCH = 2500

# Wikidata 中同盟条目与其条约之间没有任何链接、但关系有明确出处的少数情况（人工维护，注明依据）：
#   英葡同盟（Q2838032）：1373 年英葡条约（伦敦条约，Q1150265）建立，1386 年温莎条约（Q717346）确认——
#   见英文维基百科「Anglo-Portuguese Alliance」条目。成员仍只取这两份条约在 Wikidata 中记录的签署方/参与方。
CURATED_LINKS = {"Q2838032": ["Q1150265", "Q717346"]}
ALLIANCE_NAME = re.compile(r"alliance|league|pact|entente|treaty|coalition|axis|union", re.I)


def batches(ids):
    ids = sorted(ids)
    for k in range(0, len(ids), BATCH):
        yield k, ids[k:k + BATCH], "VALUES ?t { " + " ".join(f"wd:{x}" for x in ids[k:k + BATCH]) + " }"


def main():
    states = {s["id"]: s for s in json.loads(gzip.decompress((DATA / "states.json.gz").read_bytes()))}
    recs = {}
    for b in q("tr_core", f"?t wdt:P31/wdt:P279* {TREATY}; wikibase:sitelinks ?sl. FILTER(?sl >= 2)", "?t ?sl", ""):
        recs[qid(v(b, "t"))] = {"id": qid(v(b, "t")), "sl": int(v(b, "sl"))}
    for b in q("tr_core_sig", f"?t wdt:P31/wdt:P279* {TREATY}; wdt:P1891 ?x; wikibase:sitelinks ?sl.", "?t ?sl", ""):
        recs.setdefault(qid(v(b, "t")), {"id": qid(v(b, "t")), "sl": int(v(b, "sl"))})
    print("treaties:", len(recs), flush=True)
    types = collections.defaultdict(set)
    for k, ids, core in batches(recs):
        sub = {x: recs[x] for x in ids}
        labels_for(f"tr{k}", core, "t", sub)
        for prop, fld in (("P585", "signed"), ("P580", "start"), ("P571", "inception"), ("P7588", "effective"),
                          ("P582", "end"), ("P576", "dissolved")):
            for b in q(f"tr{k}_{prop}", core, "?t ?d ?dp", f"?t p:{prop}/psv:{prop} ?tv. ?tv wikibase:timeValue ?d; wikibase:timePrecision ?dp."):
                r = recs[qid(v(b, "t"))]
                t = parse_time(v(b, "d"), v(b, "dp"))
                if t and (fld not in r or (fld in ("signed", "start", "inception", "effective") and t["y"] < r[fld]["y"])):
                    r[fld] = t
        for prop in ("P1891", "P710"):
            for b in q(f"tr{k}_{prop}", core, "?t ?p", f"?t wdt:{prop} ?p."):
                r = recs[qid(v(b, "t"))]
                p = qid(v(b, "p"))
                if p in states:
                    lst = r.setdefault("parties", [])
                    if not any(x["s"] == p for x in lst):
                        lst.append({"s": p, "via": prop})
                else:
                    r[f"other_{prop}"] = r.get(f"other_{prop}", 0) + 1
        # 签署方是个人时，其「代表」限定（P1891 + P1268 represents）给出所代表的国家（如维也纳会议最后议定书）
        for b in q(f"tr{k}_rep", core, "?t ?p", "?t p:P1891 ?st. ?st pq:P1268 ?p."):
            r = recs[qid(v(b, "t"))]
            p = qid(v(b, "p"))
            if p in states:
                lst = r.setdefault("parties", [])
                if not any(x["s"] == p for x in lst):
                    lst.append({"s": p, "via": "P1268"})
            else:
                r.setdefault("other_reps", [])
                if p not in r["other_reps"]:
                    r["other_reps"].append(p)
        # 没有签署方/参与方时，用条约的「国家」P17（如 1386 年温莎条约：英格兰王国、葡萄牙王国）
        for b in q(f"tr{k}_P17", core, "?t ?p", "?t wdt:P17 ?p."):
            r = recs[qid(v(b, "t"))]
            p = qid(v(b, "p"))
            if p in states and not any(x["via"] in ("P1891", "P710") for x in r.get("parties", [])):
                lst = r.setdefault("parties", [])
                if not any(x["s"] == p for x in lst):
                    lst.append({"s": p, "via": "P17"})
        for b in q(f"tr{k}_type", core, "?t ?c", "?t wdt:P31 ?c."):
            types[qid(v(b, "t"))].add(qid(v(b, "c")))
        for site, fld in (("https://zh.wikisource.org/", "zhws"), ("https://en.wikisource.org/", "enws")):
            for b in q(f"tr{k}_{fld}", core, "?t ?title", f"?w schema:about ?t; schema:isPartOf <{site}>; schema:name ?title."):
                recs[qid(v(b, "t"))][fld] = v(b, "title")
        for b in q(f"tr{k}_P953", core, "?t ?u", "?t wdt:P953 ?u."):
            recs[qid(v(b, "t"))].setdefault("fulltext", v(b, "u"))
        # 签订地点 P1071（含中英文名与坐标）
        for b in q(f"tr{k}_P1071", core, "?t ?loc ?lz ?le ?co",
                   '?t wdt:P1071 ?loc. OPTIONAL { ?loc rdfs:label ?lz. FILTER(LANG(?lz) IN ("zh-hans","zh-cn","zh")) } '
                   'OPTIONAL { ?loc rdfs:label ?le. FILTER(LANG(?le) = "en") } OPTIONAL { ?loc wdt:P625 ?co. }'):
            r = recs[qid(v(b, "t"))]
            lid = qid(v(b, "loc"))
            locs = r.setdefault("location", [])
            cur = next((x for x in locs if x["id"] == lid), None)
            if cur is None:
                cur = {"id": lid}
                locs.append(cur)
            if v(b, "lz") and not cur.get("zh"):
                cur["zh"] = t2s(v(b, "lz"))
            if v(b, "le"):
                cur.setdefault("en", v(b, "le"))
            if v(b, "co") and "coord" not in cur:
                cur["coord"] = parse_point(v(b, "co"))
        # 条约所属国家 P17（另存一份，签署方缺失时上面已并入 parties）
        for b in q(f"tr{k}_P17", core, "?t ?p", "?t wdt:P17 ?p."):
            r = recs[qid(v(b, "t"))]
            r.setdefault("countries", [])
            if qid(v(b, "p")) not in r["countries"]:
                r["countries"].append(qid(v(b, "p")))
    # 类型名
    tids = sorted({c for s in types.values() for c in s})
    tl = {}
    for k in range(0, len(tids), BATCH):
        vals = " ".join(f"wd:{x}" for x in tids[k:k + BATCH])
        for b in cached(f"tr_typelab{k}", f'SELECT ?x ?l WHERE {{ VALUES ?x {{ {vals} }} ?x rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","zh-hant","en")) }}'):
            tl.setdefault(qid(v(b, "x")), {})[b["l"]["xml:lang"]] = b["l"]["value"]
    for t, cs in types.items():
        out = []
        for c in sorted(cs):
            z, _ = pick_zh(tl.get(c, {}))
            out.append({"id": c, "zh": t2s(z) if z else None, "en": tl.get(c, {}).get("en")})
        recs[t]["types"] = out
    # 「代表」是君主等个人时：按 Wikidata 的国家元首记录（政权的 P35 及任期）找出他当时代表的政权
    hos = collections.defaultdict(list)
    for st in states.values():
        for h in st.get("hos", []):
            if h.get("v"):
                hos[h["v"]].append((st["id"], h.get("from"), h.get("to")))
    for r in recs.values():
        d = tdate(r)
        for p in r.get("other_reps", []):
            hits = [sid for sid, f, t in hos.get(p, []) if d and f and f["y"] <= d["y"] and (not t or d["y"] <= t["y"])]
            for sid in hits:
                lst_ = r.setdefault("parties", [])
                if not any(x["s"] == sid for x in lst_):
                    lst_.append({"s": sid, "via": "P1268+P35", "rep": p})
    lst = sorted(recs.values(), key=lambda r: -r["sl"])
    write_gz(DATA / "treaties.json.gz", lst)
    print("with >=1 state party:", sum(1 for r in lst if r.get("parties")),
          ">=2:", sum(1 for r in lst if len(r.get("parties", [])) >= 2), flush=True)
    feed_alliances(recs, states)


def tdate(r):
    return r.get("effective") or r.get("signed") or r.get("start") or r.get("inception")


def feed_alliances(recs, states):
    al = json.loads(gzip.decompress((DATA / "alliances.json.gz").read_bytes()))
    al = [a for a in al if a.get("source") != "treaty"]      # 重复运行时先去掉上次追加的
    have = {a["id"] for a in al}
    core = f"VALUES ?ar {{ {ALLIANCE_ROOTS} }} ?a wdt:P31/wdt:P279* ?ar; wikibase:sitelinks ?asl. FILTER(?asl >= 3)"
    all_al = {qid(v(b, "a")) for b in q("al_core", core, "?a ?asl", "")}
    # 同盟条目 ↔ 条约 的互相引用
    links = collections.defaultdict(set)
    ids = sorted(all_al - have)
    for k in range(0, len(ids), BATCH):
        vals = "VALUES ?a { " + " ".join(f"wd:{x}" for x in ids[k:k + BATCH]) + " }"
        for b in cached(f"al_tr_out{k}", f"SELECT DISTINCT ?a ?t WHERE {{ {vals} ?a ?p ?t. ?t wdt:P31/wdt:P279* {TREATY}. }}"):
            links[qid(v(b, "a"))].add(qid(v(b, "t")))
        for b in cached(f"al_tr_in{k}", f"SELECT DISTINCT ?a ?t WHERE {{ {vals} ?t ?p ?a. ?t wdt:P31/wdt:P279* {TREATY}. }}"):
            links[qid(v(b, "a"))].add(qid(v(b, "t")))
    for a, ts in CURATED_LINKS.items():
        links[a] |= set(ts)
    new = {}
    for a, ts in links.items():
        mem = []
        for t in sorted(ts, key=lambda t: (tdate(recs.get(t, {})) or {"y": 9999})["y"]):
            r = recs.get(t)
            if not r:
                continue
            for p in r.get("parties", []):
                if not any(m["s"] == p["s"] for m in mem):
                    mem.append({"s": p["s"], "from": tdate(r), "to": r.get("end") or r.get("dissolved"), "via": "treaty:" + t})
        if len(mem) >= 2:
            new[a] = {"id": a, "members": mem, "treaties": sorted(ts), "source": "treaty",
                      "curated": a in CURATED_LINKS}
    # 类型名含 alliance 的条约
    for r in recs.values():
        if r["id"] in new or r["id"] in have or len(r.get("parties", [])) < 2:
            continue
        if any(re.search(r"alliance|defen[cs]e pact|mutual defen", (t.get("en") or ""), re.I) for t in r.get("types", [])):
            d, e = tdate(r), r.get("end") or r.get("dissolved")
            new[r["id"]] = {"id": r["id"], "members": [{"s": p["s"], "from": d, "to": e, "via": "treaty:" + r["id"]} for p in r["parties"]],
                            "treaties": [r["id"]], "source": "treaty"}
    # 标签：同盟条目查标签；条约本身直接复用条约记录
    need = {k: x for k, x in new.items() if k not in recs}
    if need:
        vals = "VALUES ?a { " + " ".join(f"wd:{x}" for x in need) + " }"
        labels_for("al_tr", vals + " ?a wikibase:sitelinks ?asl.", "a", need)
        for b in q("al_tr_sl", vals, "?a ?sl", "?a wikibase:sitelinks ?sl."):
            need[qid(v(b, "a"))]["sl"] = int(v(b, "sl"))
    # 只保留名称像同盟/条约的（排除「巴勒斯坦解放组织」「英国政府」这类也被归入 alliance 子类的组织）
    new = {k: x for k, x in new.items() if k in recs or ALLIANCE_NAME.search(x.get("en") or "") or x.get("curated")}
    for k, x in new.items():
        if k in recs:
            r = recs[k]
            x.update({f: r.get(f) for f in ("zh", "en", "desc", "zhwiki", "enwiki", "sl")})
        x.setdefault("sl", 0)
        x["from"] = min((m["from"] for m in x["members"] if m["from"]), key=lambda t: t["y"], default=None)
        x["leaders"] = []
    al += sorted(new.values(), key=lambda r: -r["sl"])
    write_gz(DATA / "alliances.json.gz", al)
    print("treaty-based alliances added:", len(new), [(x.get("zh") or x.get("en")) for x in list(new.values())[:15]])


if __name__ == "__main__":
    main()
