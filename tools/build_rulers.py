"""
君主/统治者补充（尤其是前现代政权）：

1. 「担任职务」(P39) 语句带「管辖区」限定 (P1001) 指向某政权的任职记录。例：某人 P39「中国皇帝」(Q268218)，
   限定 P1001 = 唐朝、P580/P582 = 在位起止、P1365/P1366 = 前任/继任。职位本身没有 P1001（同一个「中国皇帝」职位
   跨越许多朝代），所以 build_states.py 的职位表收不到这些记录。这里按 (职位, 政权) 组成「虚拟职位」，
   ID 形如 "Q268218@Q9683"，名称仍用职位的中文名（如「中国皇帝」），并标注政权。
2. 年号（era name，Q256408 及子类，如「中国年号」「日本年号」）：起止时间 (P580/P582 或 P571/P576) 与所属政权
   (P17 / P1001 / P361)。
输出：data/rulers.json.gz {offices:[...], eras:[...]}，data/ruler_persons.json.gz（persons.json 中没有的人物）。
需在 build_states.py 之后运行。只用 Wikidata（CC0）。
"""
from __future__ import annotations

import collections
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_states import build_persons, labels_for  # noqa: E402
from wdsparql import DATA, cached, parse_time, pick_zh, qid, simplifier, v, write_gz  # noqa: E402

t2s = simplifier()
CHUNK = 1200


def load_gz(name):
    with gzip.open(DATA / name, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    states = {s["id"]: s for s in load_gz("states.json.gz")}
    known_offices = {o["id"] for o in load_gz("offices.json.gz")}
    ids = sorted(states)
    rows = []
    for k in range(0, len(ids), CHUNK):
        vals = " ".join(f"wd:{x}" for x in ids[k:k + CHUNK])
        rows += cached(f"ru_p39_{k}", f"""SELECT ?h ?pos ?s ?s0 ?sp ?e0 ?ep ?rep ?by WHERE {{ VALUES ?s {{ {vals} }}
            ?h p:P39 ?st. ?st ps:P39 ?pos; pq:P1001 ?s; wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank)
            ?h wdt:P31 wd:Q5.
            OPTIONAL {{ ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s0; wikibase:timePrecision ?sp. }}
            OPTIONAL {{ ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e0; wikibase:timePrecision ?ep. }}
            OPTIONAL {{ ?st pq:P1365 ?rep. }} OPTIONAL {{ ?st pq:P1366 ?by. }} }}""")
    offs = {}
    for b in rows:
        pos, s = qid(v(b, "pos")), qid(v(b, "s"))
        if pos in known_offices:   # 职位本身已经有 P1001（已在 offices.json 中）
            continue
        o = offs.setdefault(f"{pos}@{s}", {"id": f"{pos}@{s}", "pos": pos, "juris": [s], "holders": [], "virtual": True})
        h = {"p": qid(v(b, "h")), "from": parse_time(v(b, "s0"), v(b, "sp")), "to": parse_time(v(b, "e0"), v(b, "ep"))}
        if v(b, "rep"):
            h["prev"] = qid(v(b, "rep"))
        if v(b, "by"):
            h["next"] = qid(v(b, "by"))
        same = [x for x in o["holders"] if x["p"] == h["p"] and x["from"] == h["from"]]
        if same:
            same[0].update({k_: v_ for k_, v_ in h.items() if v_})
        else:
            o["holders"].append(h)
    # 3. 政权条目上的「国家元首职位」(P1906) /「政府首脑职位」(P1313)，如 奥斯曼帝国 → 奥斯曼帝国苏丹。
    #    只用**只属于一个政权**的职位（「中国皇帝」这类跨朝代职位会被多个政权引用，不用，以免三国时期
    #    把曹魏、蜀汉、东吴的皇帝混在一起）；任职者的任期须与该政权存在期重叠。
    hp = []
    for k in range(0, len(ids), CHUNK):
        vals = " ".join(f"wd:{x}" for x in ids[k:k + CHUNK])
        hp += cached(f"ru_hpos_{k}", f"""SELECT ?s ?pos ?prop WHERE {{ VALUES ?s {{ {vals} }}
            {{ ?s wdt:P1906 ?pos. BIND("hos" AS ?prop) }} UNION {{ ?s wdt:P1313 ?pos. BIND("hog" AS ?prop) }} }}""")
    users = collections.defaultdict(set)
    for b in hp:
        users[qid(v(b, "pos"))].add(qid(v(b, "s")))
    single = {p_: next(iter(ss)) for p_, ss in users.items() if len(ss) == 1 and p_ not in known_offices}
    plist = sorted(single)
    hrows = []
    for k in range(0, len(plist), CHUNK):
        vals = " ".join(f"wd:{x}" for x in plist[k:k + CHUNK])
        hrows += cached(f"ru_hpos_holders_{k}", f"""SELECT ?h ?pos ?s0 ?sp ?e0 ?ep ?rep ?by WHERE {{ VALUES ?pos {{ {vals} }}
            ?h p:P39 ?st. ?st ps:P39 ?pos; wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank)
            ?h wdt:P31 wd:Q5.
            OPTIONAL {{ ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s0; wikibase:timePrecision ?sp. }}
            OPTIONAL {{ ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e0; wikibase:timePrecision ?ep. }}
            OPTIONAL {{ ?st pq:P1365 ?rep. }} OPTIONAL {{ ?st pq:P1366 ?by. }} }}""")

    def yr(t):
        return t["y"] if t else None
    n_hp = 0
    for b in hrows:
        pos = qid(v(b, "pos"))
        s = single[pos]
        st_ = states.get(s, {})
        h = {"p": qid(v(b, "h")), "from": parse_time(v(b, "s0"), v(b, "sp")), "to": parse_time(v(b, "e0"), v(b, "ep"))}
        a0, b0 = yr(st_.get("from")), yr(st_.get("to"))
        hf, ht = yr(h["from"]), yr(h["to"]) or yr(h["from"])
        if hf is None or (a0 is not None and ht is not None and ht < a0 - 1) or (b0 is not None and hf > b0 + 1):
            continue
        if v(b, "rep"):
            h["prev"] = qid(v(b, "rep"))
        if v(b, "by"):
            h["next"] = qid(v(b, "by"))
        o = offs.setdefault(f"{pos}@{s}", {"id": f"{pos}@{s}", "pos": pos, "juris": [s], "holders": [], "virtual": True,
                                           "via": "P1906/P1313"})
        if not any(x["p"] == h["p"] and x["from"] == h["from"] for x in o["holders"]):
            o["holders"].append(h)
            n_hp += 1
    print("head-of-state/government positions (single-state):", len(single), "holders added:", n_hp, flush=True)
    # 没有卸任时间、但记录了继任者且继任者有即位时间的：卸任时间取继任者即位时间（标注为推断）
    for o in offs.values():
        start = {h["p"]: h["from"] for h in o["holders"] if h.get("from")}
        for h in o["holders"]:
            if not h.get("to") and h.get("next") in start:
                h["to"] = start[h["next"]]
                h["to_inferred"] = "继任者即位时间（P1366）"
    # 职位标签
    poss = sorted({o["pos"] for o in offs.values()})
    precs = {p: {"id": p, "sl": 0} for p in poss}
    for k in range(0, len(poss), 3000):
        sub = {x: precs[x] for x in poss[k:k + 3000]}
        labels_for(f"ru_pos{k}", "VALUES ?pos { " + " ".join(f"wd:{x}" for x in sub) + " }", "pos", sub)
        for b in cached(f"ru_pos{k}_sl", "SELECT ?pos ?sl WHERE { VALUES ?pos { " + " ".join(f"wd:{x}" for x in sub) + " } ?pos wikibase:sitelinks ?sl. }"):
            precs[qid(v(b, "pos"))]["sl"] = int(v(b, "sl"))
    for o in offs.values():
        p = precs.get(o["pos"], {})
        st = states.get(o["juris"][0], {})
        o.update(zh=p.get("zh"), en=p.get("en"), desc=p.get("desc"), sl=p.get("sl", 0),
                 juris_zh=st.get("zh") or st.get("en"))
    # 年号
    eras = []
    # 年号条目不多（几千个）：一次取出全部，再在本地按政权过滤（带 VALUES 的大查询会超时）
    er = cached("ru_era_all", """SELECT ?e ?s ?a ?ap ?b ?bp WHERE { ?e wdt:P31/wdt:P279* wd:Q256408.
        OPTIONAL { ?e wdt:P17|wdt:P1001|wdt:P361 ?s. }
        OPTIONAL { ?e p:P580/psv:P580 ?av. ?av wikibase:timeValue ?a; wikibase:timePrecision ?ap. }
        OPTIONAL { ?e p:P582/psv:P582 ?bv. ?bv wikibase:timeValue ?b; wikibase:timePrecision ?bp. } }""")
    by = {}
    for b_ in er:
        s_ = v(b_, "s")
        if not s_ or qid(s_) not in states:
            continue
        e = by.setdefault((qid(v(b_, "e")), qid(s_)), {"id": qid(v(b_, "e")), "state": qid(s_)})
        if v(b_, "a") and not e.get("from"):
            e["from"] = parse_time(v(b_, "a"), v(b_, "ap"))
        if v(b_, "b") and not e.get("to"):
            e["to"] = parse_time(v(b_, "b"), v(b_, "bp"))
    eids = sorted({e["id"] for e in by.values()})
    erecs = {x: {"id": x, "sl": 0} for x in eids}
    for k in range(0, len(eids), 3000):
        sub = {x: erecs[x] for x in eids[k:k + 3000]}
        labels_for(f"ru_era{k}", "VALUES ?e { " + " ".join(f"wd:{x}" for x in sub) + " }", "e", sub)
    for e in by.values():
        r = erecs.get(e["id"], {})
        e["zh"], e["en"] = r.get("zh"), r.get("en")
        if e.get("from"):
            eras.append(e)
    # 人物
    have = {p["id"] for p in load_gz("persons.json.gz")}
    pids = {h["p"] for o in offs.values() for h in o["holders"]} - have
    persons = build_persons(pids, extra_name="rup") if pids else {}
    write_gz(DATA / "rulers.json.gz", {"offices": sorted(offs.values(), key=lambda o: -o["sl"]), "eras": eras})
    write_gz(DATA / "ruler_persons.json.gz", list(persons.values()))
    cnt = collections.Counter(o["juris"][0] for o in offs.values())
    print("virtual offices:", len(offs), "holders:", sum(len(o["holders"]) for o in offs.values()),
          "states covered:", len(cnt), "eras:", len(eras), "new persons:", len(persons))


if __name__ == "__main__":
    main()
