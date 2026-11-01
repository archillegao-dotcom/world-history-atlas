#!/usr/bin/env python3
"""
构建「国家/政权」「职位」「阵营/同盟」三份数据（Wikidata，经 QLever SPARQL），供第二阶段功能使用：

data/states.json.gz     政权：中英文名、别名、存在期、首都（含起止）、政体 P122、意识形态 P1142、
                        国家元首 P35 / 政府首脑 P6（含起止）、国旗 P41、前身/后继 P1365/P1366、维基条目
data/offices.json.gz    职位：管辖区 P1001 为上述政权的职位（如「中华民国总统」「行政院院长」），
                        任职者 P39（含起止限定），所领导机构 P2389，维基条目；任职者过多的（如议员）不收
data/persons.json.gz    上述元首/首脑/任职者/阵营领导人的基本信息（中英文名、生卒、所属政党 P102 含起止、维基条目）
data/alliances.json.gz  阵营/同盟：military alliance、multinational military coalition、koinon、alliance 及其子类，
                        成员来自 P527/P710/P1891（阵营条目上）与 P463「成员属于」（成员国条目上），含加入/退出时间；
                        领导/核心人物来自 P488 主席、P35、P6、P1037 负责人、P112 创始人、P3342 重要人物
data/polity_map.json.gz 地图政权（historical-basemaps 的多边形）→ Wikidata 政权候选列表（见 build_polity_map）
只使用 Wikidata 中的数据；没有就留空。
"""
from __future__ import annotations

import collections
import re
import gzip
import json
import sys

from wdsparql import DATA, cached, parse_point, parse_time, pick_zh, qid, simplifier, v, write_gz

STATE_ROOTS = "wd:Q6256 wd:Q3024240 wd:Q7275 wd:Q1250464 wd:Q3624078 wd:Q48349 wd:Q417175 wd:Q28171280 wd:Q164950"
STATE_MIN_SL = 5
ALLIANCE_ROOTS = "wd:Q878249 wd:Q100906234 wd:Q1778834 wd:Q1127126"
OFFICE_MAX_HOLDERS = 400
t2s = simplifier()
RANKS = {"http://wikiba.se/ontology#PreferredRank": 0, "http://wikiba.se/ontology#NormalRank": 1}

S_CORE = (f"VALUES ?r {{ {STATE_ROOTS} }} ?s wdt:P31/wdt:P279* ?r; wikibase:sitelinks ?ssl. "
          f"FILTER(?ssl >= {STATE_MIN_SL}) FILTER NOT EXISTS {{ ?s wdt:P31 wd:Q5 }}")


def q(name, core, sel, body):
    return cached(name, f"SELECT DISTINCT {sel} WHERE {{ {core} {body} }}")


def qual_body(subj, prop):
    """某属性的语句值 + 起止限定（P580/P582）+ 等级。"""
    return (f"?{subj} p:{prop} ?st. ?st ps:{prop} ?val; wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank) "
            "OPTIONAL { ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s0; wikibase:timePrecision ?sp. } "
            "OPTIONAL { ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e0; wikibase:timePrecision ?ep. }")


def qual_rows(rows, subj):
    """-> {subj_qid: [{"v": qid或字面值, "from": t, "to": t, "pref": bool}]}"""
    out = collections.defaultdict(list)
    for b in rows:
        val = v(b, "val")
        rec = {"v": qid(val) if val and val.startswith("http://www.wikidata.org/entity/") else val,
               "from": parse_time(v(b, "s0"), v(b, "sp")), "to": parse_time(v(b, "e0"), v(b, "ep"))}
        if RANKS.get(v(b, "rank")) == 0:
            rec["pref"] = True
        lst = out[qid(v(b, subj))]
        if rec not in lst:
            lst.append(rec)
    return out


def labels_for(name, core, subj, recs, with_alias=False):
    labs = collections.defaultdict(dict)
    for b in q(f"{name}_labels", core, f"?{subj} ?l",
               f'?{subj} rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","zh-hant","zh-tw","en"))'):
        labs[qid(v(b, subj))][b["l"]["xml:lang"]] = b["l"]["value"]
    descs = collections.defaultdict(dict)
    for b in q(f"{name}_desc", core, f"?{subj} ?d",
               f'?{subj} schema:description ?d. FILTER(LANG(?d) IN ("zh","zh-cn","zh-hans","en"))'):
        descs[qid(v(b, subj))][b["d"]["xml:lang"]] = b["d"]["value"]
    for site, fld in (("https://zh.wikipedia.org/", "zhwiki"), ("https://en.wikipedia.org/", "enwiki")):
        for b in q(f"{name}_{fld}", core, f"?{subj} ?title", f"?w schema:about ?{subj}; schema:isPartOf <{site}>; schema:name ?title."):
            r = recs.get(qid(v(b, subj)))
            if r is not None:
                r[fld] = v(b, "title")
    if with_alias:
        for b in q(f"{name}_alias", core, f"?{subj} ?a", f'?{subj} skos:altLabel ?a. FILTER(LANG(?a) = "en")'):
            r = recs.get(qid(v(b, subj)))
            if r is not None:
                r.setdefault("aliases", []).append(b["a"]["value"])
    for k, r in recs.items():
        ls = labs.get(k, {})
        z, _ = pick_zh(ls)
        r["zh"] = t2s(z) if z else None
        r["en"] = ls.get("en")
        ds = descs.get(k, {})
        zd, _ = pick_zh(ds)
        r["desc"] = t2s(zd) if zd else ds.get("en")


def life(name, core, subj, recs):
    for prop, fld in (("P571", "from"), ("P576", "to"), ("P569", "born"), ("P570", "died")):
        rows = q(f"{name}_{prop}", core, f"?{subj} ?t ?tp ?rank",
                 f"?{subj} p:{prop} ?st. ?st wikibase:rank ?rank; psv:{prop} ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp.")
        for b in rows:
            r = recs.get(qid(v(b, subj)))
            t = parse_time(v(b, "t"), v(b, "tp"))
            if r is None or not t or v(b, "rank") not in RANKS:
                continue
            old = r.get(fld)
            better = (not old or (RANKS[v(b, "rank")] == 0 and not r.get("_p" + fld)) or
                      (fld in ("from", "born") and t["y"] < old["y"] and not r.get("_p" + fld)) or
                      (fld in ("to", "died") and t["y"] > old["y"] and not r.get("_p" + fld)))
            if better:
                r[fld] = t
                if RANKS[v(b, "rank")] == 0:
                    r["_p" + fld] = True
    for r in recs.values():
        for k in [k for k in r if k.startswith("_p")]:
            del r[k]


# ------------------------------------------------------------------ states
def build_states():
    recs = {}
    for b in q("st_core", S_CORE, "?s ?ssl", ""):
        recs[qid(v(b, "s"))] = {"id": qid(v(b, "s")), "sl": int(v(b, "ssl"))}
    print("states:", len(recs), flush=True)
    labels_for("st", S_CORE, "s", recs, with_alias=True)
    life("st", S_CORE, "s", recs)
    # 首都（含起止）与首都坐标
    caps = qual_rows(q("st_cap", S_CORE, "?s ?val ?s0 ?sp ?e0 ?ep ?rank", qual_body("s", "P36")), "s")
    capco = {qid(v(b, "c")): parse_point(v(b, "co")) for b in q("st_capco", S_CORE, "?c ?co", "?s wdt:P36 ?c. ?c wdt:P625 ?co.")}
    caplab = {}
    for b in q("st_caplab", S_CORE, "?c ?l", '?s wdt:P36 ?c. ?c rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","en"))'):
        caplab.setdefault(qid(v(b, "c")), {})[b["l"]["xml:lang"]] = b["l"]["value"]
    for s, lst in caps.items():
        if s in recs:
            for c in lst:
                c["coord"] = capco.get(c["v"])
                z, _ = pick_zh(caplab.get(c["v"], {}))
                c["name"] = t2s(z) if z else caplab.get(c["v"], {}).get("en")
            recs[s]["capitals"] = lst
    for b in q("st_coord", S_CORE, "?s ?co", "?s wdt:P625 ?co."):
        r = recs.get(qid(v(b, "s")))
        if r is not None and "coord" not in r:
            r["coord"] = parse_point(v(b, "co"))
    # 政体、意识形态、元首、首脑、官方宗教不取；国旗；前身/后继
    for prop, fld in (("P122", "gov"), ("P1142", "ideology"), ("P35", "hos"), ("P6", "hog"),
                      ("P1365", "replaces"), ("P1366", "replaced_by"), ("P41", "flag"), ("P30", "continent")):
        for s, lst in qual_rows(q(f"st_{prop}", S_CORE, "?s ?val ?s0 ?sp ?e0 ?ep ?rank", qual_body("s", prop)), "s").items():
            if s in recs:
                recs[s][fld] = lst
    # 政体/意识形态的中文名
    terms = {}
    for prop in ("P122", "P1142"):
        for b in q(f"st_{prop}_lab", S_CORE, "?x ?l", f'?s wdt:{prop} ?x. ?x rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","en"))'):
            terms.setdefault(qid(v(b, "x")), {})[b["l"]["xml:lang"]] = b["l"]["value"]
    termnames = {}
    for k, ls in terms.items():
        z, _ = pick_zh(ls)
        termnames[k] = {"zh": t2s(z) if z else None, "en": ls.get("en")}
    for r in recs.values():
        for fld in ("gov", "ideology"):
            for x in r.get(fld, []):
                x.update(termnames.get(x["v"], {}))
        if r.get("flag"):
            r["flag"] = r["flag"][0]["v"]  # Commons 文件名
    write_gz(DATA / "states.json.gz", sorted(recs.values(), key=lambda r: -r["sl"]))
    return recs


# ------------------------------------------------------------------ offices & persons
def build_offices(states):
    core = (f"{S_CORE} ?pos wdt:P1001 ?s; wikibase:sitelinks ?psl. FILTER(?psl >= 3) "
            "FILTER NOT EXISTS { ?pos wdt:P31 wd:Q5 }")
    offices = {}
    for b in q("of_core", core, "?pos ?s ?psl", ""):
        o = offices.setdefault(qid(v(b, "pos")), {"id": qid(v(b, "pos")), "sl": int(v(b, "psl")), "juris": []})
        if qid(v(b, "s")) not in o["juris"]:
            o["juris"].append(qid(v(b, "s")))
    # 任职者：按职位分批（VALUES）查询，避免全库 P39 连接超时
    ids = sorted(offices)
    hold = []
    for k in range(0, len(ids), 1500):
        vals = " ".join(f"wd:{x}" for x in ids[k:k + 1500])
        hold += cached(f"of_holders_{k}", f"""SELECT ?pos ?h ?s0 ?sp ?e0 ?ep WHERE {{ VALUES ?pos {{ {vals} }}
            ?h p:P39 ?st. ?st ps:P39 ?pos; wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank)
            OPTIONAL {{ ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s0; wikibase:timePrecision ?sp. }}
            OPTIONAL {{ ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e0; wikibase:timePrecision ?ep. }} }}""")
    # 任职者计数（过滤掉「议员」这类多人职位）
    cnt = collections.Counter()
    for b in hold:
        cnt[qid(v(b, "pos"))] += 1
    keep = {k for k, n in cnt.items() if n <= OFFICE_MAX_HOLDERS}
    offices = {k: o for k, o in offices.items() if k in keep}
    for b in hold:
        o = offices.get(qid(v(b, "pos")))
        if o is None:
            continue
        h = {"p": qid(v(b, "h")), "from": parse_time(v(b, "s0"), v(b, "sp")), "to": parse_time(v(b, "e0"), v(b, "ep"))}
        if h not in o.setdefault("holders", []):
            o["holders"].append(h)
    print("offices kept:", len(offices), "of", len(cnt), flush=True)
    ids = sorted(offices)
    for k in range(0, len(ids), 3000):
        sub = {x: offices[x] for x in ids[k:k + 3000]}
        ocore = "VALUES ?pos { " + " ".join(f"wd:{x}" for x in sub) + " }"
        labels_for(f"of{k}", ocore, "pos", sub)
        for b in q(f"of{k}_org", ocore, "?pos ?org", "?pos wdt:P2389 ?org."):
            offices[qid(v(b, "pos"))].setdefault("orgs", []).append(qid(v(b, "org")))
    # 机构（P2389）
    orgs = sorted({x for o in offices.values() for x in o.get("orgs", [])})
    orgrecs = {k: {"id": k, "sl": 0} for k in orgs}
    for k in range(0, len(orgs), 3000):
        sub = {x: orgrecs[x] for x in orgs[k:k + 3000]}
        labels_for(f"org{k}", "VALUES ?org { " + " ".join(f"wd:{x}" for x in sub) + " }", "org", sub)
    # 人物：元首、首脑、任职者
    pids = {h["p"] for o in offices.values() for h in o.get("holders", [])}
    for s in states.values():
        for fld in ("hos", "hog"):
            pids.update(x["v"] for x in s.get(fld, []) if x["v"] and x["v"].startswith("Q"))
    return offices, orgrecs, pids


def build_persons(pids, extra_name="pe"):
    pids = sorted(pids)
    recs = {p: {"id": p} for p in pids}
    for k in range(0, len(pids), 3000):
        vals = " ".join(f"wd:{x}" for x in pids[k:k + 3000])
        core = f"VALUES ?p {{ {vals} }}"
        labels_for(f"{extra_name}{k}", core, "p", {x: recs[x] for x in pids[k:k + 3000]})
        life(f"{extra_name}{k}", core, "p", recs)
        for p, lst in qual_rows(q(f"{extra_name}{k}_party", core, "?p ?val ?s0 ?sp ?e0 ?ep ?rank", qual_body("p", "P102")), "p").items():
            recs[p]["party"] = lst
        for b in q(f"{extra_name}{k}_sl", core, "?p ?sl", "?p wikibase:sitelinks ?sl."):
            recs[qid(v(b, "p"))]["sl"] = int(v(b, "sl"))
        for b in q(f"{extra_name}{k}_img", core, "?p ?img", "?p wdt:P18 ?img."):
            r = recs[qid(v(b, "p"))]
            r.setdefault("img", v(b, "img").rsplit("/", 1)[-1])
    # 政党中文名
    parties = sorted({x["v"] for r in recs.values() for x in r.get("party", []) if x["v"] and re.fullmatch(r"Q\d+", x["v"])})
    pn = {}
    for k in range(0, len(parties), 3000):
        vals = " ".join(f"wd:{x}" for x in parties[k:k + 3000])
        for b in cached(f"party_lab{k}", f'SELECT ?x ?l WHERE {{ VALUES ?x {{ {vals} }} ?x rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","en")) }}'):
            pn.setdefault(qid(v(b, "x")), {})[b["l"]["xml:lang"]] = b["l"]["value"]
    for r in recs.values():
        for x in r.get("party", []):
            z, _ = pick_zh(pn.get(x["v"], {}))
            x["zh"], x["en"] = (t2s(z) if z else None), pn.get(x["v"], {}).get("en")
    return recs


# ------------------------------------------------------------------ alliances
def build_alliances(states):
    core = f"VALUES ?ar {{ {ALLIANCE_ROOTS} }} ?a wdt:P31/wdt:P279* ?ar; wikibase:sitelinks ?asl. FILTER(?asl >= 3)"
    al = {}
    for b in q("al_core", core, "?a ?asl", ""):
        al[qid(v(b, "a"))] = {"id": qid(v(b, "a")), "sl": int(v(b, "asl")), "members": []}
    mem = collections.defaultdict(list)
    for prop in ("P527", "P710", "P1891"):
        for a, lst in qual_rows(q(f"al_{prop}", core, "?a ?val ?s0 ?sp ?e0 ?ep ?rank", qual_body("a", prop)), "a").items():
            for m in lst:
                if m["v"] in states:
                    mem[a].append({"s": m["v"], "from": m["from"], "to": m["to"], "via": prop})
    # 反向：成员国条目上的 P463「成员属于」
    rows = q("al_P463", core, "?a ?m ?s0 ?sp ?e0 ?ep",
             "?m p:P463 ?st. ?st ps:P463 ?a; wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank) "
             "OPTIONAL { ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s0; wikibase:timePrecision ?sp. } "
             "OPTIONAL { ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e0; wikibase:timePrecision ?ep. }")
    for b in rows:
        m = qid(v(b, "m"))
        if m in states:
            mem[qid(v(b, "a"))].append({"s": m, "from": parse_time(v(b, "s0"), v(b, "sp")),
                                        "to": parse_time(v(b, "e0"), v(b, "ep")), "via": "P463"})
    for a, lst in mem.items():
        if a in al:
            # 同一成员多条来源（P527/P710/P1891/P463）：有日期的记录全部保留（可能是多段成员期，
            # 也可能是不同来源互相矛盾——运行时任一段有效即视为成员）；都没有日期时只留一条
            byst = collections.defaultdict(list)
            for m in lst:
                byst[m["s"]].append(m)
            out = []
            for s_, ms in byst.items():
                dated = [m for m in ms if m["from"] or m["to"]]
                seen = set()
                for m in (dated or ms[:1]):
                    k = (json.dumps(m["from"]), json.dumps(m["to"]))
                    if k not in seen:
                        seen.add(k)
                        out.append(m)
            al[a]["members"] = out
    al = {k: r for k, r in al.items() if len(r["members"]) >= 2}
    print("alliances with >=2 state members:", len(al), flush=True)
    acore = core + " FILTER(?a IN (" + ",".join(f"wd:{k}" for k in al) + "))"
    labels_for("al", acore, "a", al)
    life("al", acore, "a", al)
    for prop in ("P580", "P582"):
        for b in q(f"al_t{prop}", acore, "?a ?t ?tp", f"?a p:{prop}/psv:{prop} ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp."):
            r = al[qid(v(b, "a"))]
            fld = "from" if prop == "P580" else "to"
            r.setdefault(fld, parse_time(v(b, "t"), v(b, "tp")))
    # 没有成立/解散时间时，用「性质」(P31) 声明上的起止限定（如「同盟国」1939–1945）
    for prop, fld in (("P580", "from"), ("P582", "to")):
        for b in q(f"al_p31{prop}", acore, "?a ?t ?tp", f"?a p:P31 ?s31. ?s31 pqv:{prop} ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp."):
            r = al[qid(v(b, "a"))]
            if not r.get(fld):
                r[fld] = parse_time(v(b, "t"), v(b, "tp"))
    leaders = collections.defaultdict(list)
    for prop in ("P488", "P35", "P6", "P1037", "P112", "P3342"):
        for a, lst in qual_rows(q(f"al_{prop}", acore, "?a ?val ?s0 ?sp ?e0 ?ep ?rank", qual_body("a", prop)), "a").items():
            for x in lst:
                if x["v"] and x["v"].startswith("Q"):
                    leaders[a].append({"p": x["v"], "role": prop, "from": x["from"], "to": x["to"]})
    for a, lst in leaders.items():
        al[a]["leaders"] = lst
    return al


def main():
    states = build_states()
    offices, orgs, pids = build_offices(states)
    alliances = build_alliances(states)
    for a in alliances.values():
        pids.update(x["p"] for x in a.get("leaders", []))
    persons = build_persons(pids)
    # 只保留人类（P39/P35 偶尔指向机构）
    write_gz(DATA / "offices.json.gz", sorted(offices.values(), key=lambda r: -r["sl"]))
    write_gz(DATA / "orgs.json.gz", list(orgs.values()))
    write_gz(DATA / "persons.json.gz", list(persons.values()))
    write_gz(DATA / "alliances.json.gz", sorted(alliances.values(), key=lambda r: -r["sl"]))


if __name__ == "__main__":
    main()
