#!/usr/bin/env python3
"""
从 Wikidata 预先抓取「事件」与「人物」数据（全时间范围），缓存到 data/，应用离线可用。

方法（见 README「数据是怎么来的」）：
- 事件：Wikidata 中属于「事件/发生的事」(Q1190554 occurrence 及其子类) 的条目，
        有 P585 时间点 或 P580 开始时间，sitelinks（维基语言版本数）≥ 门槛；
- 人物：P31=人类，P106 职业属于该类别（文学家/哲学家/政治家…），sitelinks ≥ 门槛；
- 每个属性单独一个「分面」查询（时间、坐标、国家、标签、维基链接…），在 Python 中按 QID 合并，
  这样每个查询都很便宜，不会超时；
- 坐标：事件 P625 > 地点 P276 的坐标 > 国家 P17 的坐标（粗略，标记 coord_src）；人物用出生地 P19 坐标；
- 中文：zh-cn > zh-hans > zh > zh-hant …，统一 OpenCC 繁→简；没有中文就用英文。
只使用 Wikidata 中真实存在的数据。

用法:
  python tools/build_wikidata.py                   # 事件 + 全部人物类别 + 国家表
  python tools/build_wikidata.py --only people --cats writer
环境变量 WHA_SPARQL_ENDPOINT 可切换端点；WHA_REFRESH=1 强制重新抓取。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time

import requests

from wdsparql import (DATA, UA, cached, parse_point, parse_time, pick_zh, qid, simplifier, v, write_gz)

YEAR_MIN, YEAR_MAX = -3600, dt.date.today().year

# 人物类别：id -> (中文名, 职业 QID, 最低 sitelinks, 最多保留条数)
#   文学家：writer 作家, poet 诗人, novelist 小说家, playwright 剧作家, children's writer 儿童文学作家, essayist 散文家
#   哲学家：philosopher
#   政治家：politician 政治家, monarch 君主, statesperson 政治家/国务活动家, head of state 国家元首, president 总统
PEOPLE_CATEGORIES = {
    "writer": ("文学家", ["Q36180", "Q49757", "Q6625963", "Q214917", "Q4853732", "Q11774202"], 10, 40000),
    "philosopher": ("哲学家", ["Q4964182"], 6, 15000),
    "politician": ("政治家", ["Q82955", "Q116", "Q372436", "Q48352", "Q30461"], 12, 40000),
}

EVENT_MIN_SITELINKS = 6
EVENT_MAX = 90000

# 有日期、也属于 occurrence 子类，但对历史地图是噪声的类型（按 P31 精确排除）
NON_EVENT_TYPES = {
    "Q18340514",  # events in a specific year or time period（「1789年法国」这类年度概览）
    "Q3186692", "Q577", "Q19828", "Q39911", "Q14795564", "Q16929628",  # 年份、闰年、十年、共和历年…
    "Q27020041", "Q1539532",  # sports season / sports season of a club
    "Q15061650", "Q46190676", "Q2990963", "Q1366722",  # 高尔夫/网球/花滑单项赛事、决赛
    "Q3464665", "Q21191270",  # 电视剧季、电视剧集
}


def lang_rows_to(recs, rows, key, field):
    for b in rows:
        r = recs.get(qid(v(b, key)))
        if r is not None and b.get(field):
            r.setdefault("_" + field, {})[b[field].get("xml:lang")] = b[field]["value"]


def finish_labels(recs):
    t2s = simplifier()
    for r in recs.values():
        labs = r.pop("_l", {})
        zh, lang = pick_zh(labs)
        r["name"] = t2s(zh) if zh else labs.get("en")
        r["lang"] = lang or ("en" if labs.get("en") else None)
        r["en_name"] = labs.get("en")
        ds = r.pop("_desc", {})
        zd, _ = pick_zh(ds)
        r["desc"] = t2s(zd) if zd else ds.get("en")


def facet(name, core, select, body):
    return cached(name, f"SELECT DISTINCT {select} WHERE {{ {core} {body} }}")


def add_common_facets(prefix, core, var, recs):
    """标签、描述、中英文维基链接。"""
    lang_rows_to(recs, facet(f"{prefix}_labels", core, f"?{var} ?l",
                             f'?{var} rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","zh-hant","zh-tw","zh-hk","en"))'), var, "l")
    lang_rows_to(recs, facet(f"{prefix}_desc", core, f"?{var} ?desc",
                             f'?{var} schema:description ?desc. FILTER(LANG(?desc) IN ("zh","zh-cn","zh-hans","zh-hant","en"))'), var, "desc")
    for site, fld in (("https://zh.wikipedia.org/", "zhwiki"), ("https://en.wikipedia.org/", "enwiki")):
        for b in facet(f"{prefix}_{fld}", core, f"?{var} ?w", f"?w schema:about ?{var}; schema:isPartOf <{site}>."):
            r = recs.get(qid(v(b, var)))
            if r is not None:
                r[fld] = v(b, "w")
    finish_labels(recs)


RANK = {"http://wikiba.se/ontology#PreferredRank": 0, "http://wikiba.se/ontology#NormalRank": 1,
        "http://wikiba.se/ontology#DeprecatedRank": 9}


def best_time(rows, recs, var, field):
    """同一属性多个值时：优先「首选」等级，其次精度高的、最早的。"""
    for b in rows:
        r = recs.get(qid(v(b, var)))
        if r is None:
            continue
        rank = RANK.get(v(b, "rank"), 1)
        if rank == 9:
            continue
        t = parse_time(v(b, "t"), v(b, "tp"))
        if not t:
            continue
        cand = (rank, -t["p"], t["y"], t["m"], t["d"])
        if field not in r or cand < r["_" + field + "_k"]:
            r[field], r["_" + field + "_k"] = t, cand
    for r in recs.values():
        r.pop("_" + field + "_k", None)


# ------------------------------------------------------------------ events
def build_events():
    recs: dict[str, dict] = {}
    for prop in ("P585", "P580"):
        core = (f"?item wdt:{prop} ?t0; wikibase:sitelinks ?sl. FILTER(?sl >= {EVENT_MIN_SITELINKS}) "
                f"?item wdt:P31/wdt:P279* wd:Q1190554 .")
        for b in facet(f"ev_{prop}_core", core, "?item ?sl", ""):
            q = qid(v(b, "item"))
            recs.setdefault(q, {"id": q, "sl": int(v(b, "sl")), "types": set(), "countries": set()})
        tm = facet(f"ev_{prop}_time", core, "?item ?t ?tp ?rank",
                   f"?item p:{prop} ?st. ?st wikibase:rank ?rank; psv:{prop} ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp.")
        best_time(tm, recs, "item", "start" if prop == "P580" else "start585")
    # P585（时间点）优先于 P580（开始时间）
    for r in recs.values():
        if "start585" in r:
            r["start"] = r.pop("start585")
    recs = {q: r for q, r in recs.items() if r.get("start") and YEAR_MIN <= r["start"]["y"] <= YEAR_MAX and r["start"]["p"] >= 7}
    print("events with dates:", len(recs), flush=True)

    core = (f"{{ ?item wdt:P585 ?t0 }} UNION {{ ?item wdt:P580 ?t0 }} ?item wikibase:sitelinks ?sl. "
            f"FILTER(?sl >= {EVENT_MIN_SITELINKS}) ?item wdt:P31/wdt:P279* wd:Q1190554 .")
    best_time(facet("ev_end", core, "?item ?t ?tp ?rank",
                    "?item p:P582 ?st. ?st wikibase:rank ?rank; psv:P582 ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp."),
              recs, "item", "end")
    for b in facet("ev_types", core, "?item ?type", "?item wdt:P31 ?type."):
        r = recs.get(qid(v(b, "item")))
        if r is not None:
            r["types"].add(qid(v(b, "type")))
    for b in facet("ev_country", core, "?item ?c", "?item wdt:P17 ?c."):
        r = recs.get(qid(v(b, "item")))
        if r is not None:
            r["countries"].add(qid(v(b, "c")))
    # 坐标：自身 > 地点(P276) > 国家（国家坐标在 countries 步骤中补）
    for name, body, src in (("ev_coord", "?item wdt:P625 ?coord.", "self"),
                            ("ev_lcoord", "?item wdt:P276 ?loc. ?loc wdt:P625 ?coord.", "location")):
        for b in facet(name, core, "?item ?coord", body):
            r = recs.get(qid(v(b, "item")))
            pt = parse_point(v(b, "coord"))
            if r is not None and pt and "coord" not in r:
                r["coord"], r["coord_src"] = pt, src
    # 参与方（P710，如交战国）的坐标或其首都坐标：作为额外候选点。战争/条约常常没有自身坐标，
    # 或者 P276 只写了「东亚」这类大区域，用参与方可让各参与国的面板都能看到这一事件。
    for b in facet("ev_pcoord", core, "?item ?coord",
                   "?item wdt:P710 ?pt. { ?pt wdt:P625 ?coord } UNION { ?pt wdt:P36 ?cap. ?cap wdt:P625 ?coord }"):
        r = recs.get(qid(v(b, "item")))
        pt = parse_point(v(b, "coord"))
        if r is not None and pt:
            lst = r.setdefault("coords", [])
            if pt not in lst and len(lst) < 8:
                lst.append(pt)
    recs = {q: r for q, r in recs.items() if not (r["types"] & NON_EVENT_TYPES)}
    add_common_facets("ev", core, "item", recs)
    out = sorted(recs.values(), key=lambda r: -r["sl"])[:EVENT_MAX]
    for r in out:
        r["types"], r["countries"] = sorted(r["types"]), sorted(r["countries"])
    write_gz(DATA / "events.json.gz", out)


# ------------------------------------------------------------------ people
def build_people(cat):
    zh, occs, min_sl, cap = PEOPLE_CATEGORIES[cat]
    vals = " ".join(f"wd:{o}" for o in occs)
    core = f"VALUES ?occ {{ {vals} }} ?p wdt:P106 ?occ; wikibase:sitelinks ?sl. FILTER(?sl >= {min_sl}) ?p wdt:P31 wd:Q5."
    recs: dict[str, dict] = {}
    for b in facet(f"p_{cat}_core", core, "?p ?sl ?occ", ""):
        q = qid(v(b, "p"))
        r = recs.setdefault(q, {"id": q, "sl": int(v(b, "sl")), "types": set(), "countries": set()})
        r["types"].add(qid(v(b, "occ")))
    best_time(facet(f"p_{cat}_birth", core, "?p ?t ?tp ?rank",
                    "?p p:P569 ?st. ?st wikibase:rank ?rank; psv:P569 ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp."),
              recs, "p", "birth")
    best_time(facet(f"p_{cat}_death", core, "?p ?t ?tp ?rank",
                    "?p p:P570 ?st. ?st wikibase:rank ?rank; psv:P570 ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp."),
              recs, "p", "death")
    recs = {q: r for q, r in recs.items() if r.get("birth") and r["birth"]["y"] >= YEAR_MIN - 100}
    for b in facet(f"p_{cat}_coord", core, "?p ?coord", "?p wdt:P19 ?bpl. ?bpl wdt:P625 ?coord."):
        r = recs.get(qid(v(b, "p")))
        pt = parse_point(v(b, "coord"))
        if r is not None and pt and "coord" not in r:
            r["coord"] = pt
    for b in facet(f"p_{cat}_cit", core, "?p ?c", "?p wdt:P27 ?c."):
        r = recs.get(qid(v(b, "p")))
        if r is not None:
            r["countries"].add(qid(v(b, "c")))
    add_common_facets(f"p_{cat}", core, "p", recs)
    out = sorted(recs.values(), key=lambda r: -r["sl"])[:cap]
    for r in out:
        r["types"], r["countries"] = sorted(r["types"]), sorted(r["countries"])
    write_gz(DATA / f"people_{cat}.json.gz", out)


# ------------------------------------------------------------------ countries
def build_countries():
    """所有数据中出现的国家/国籍 QID -> 名称（中英文+英文别名）与坐标。
    名称用于无坐标条目按名称匹配地图政权；坐标用于只有「国家」信息的事件的粗略定位。"""
    import gzip
    qids: set[str] = set()
    for f in [DATA / "events.json.gz", *DATA.glob("people_*.json.gz")]:
        for r in json.loads(gzip.decompress(f.read_bytes())):
            qids.update(r.get("countries", []))
    out = {}
    todo = sorted(qids)
    for k in range(0, len(todo), 50):
        r = requests.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities", "ids": "|".join(todo[k:k + 50]), "props": "labels|aliases|claims",
            "languages": "en|zh|zh-hans|zh-cn", "format": "json"}, headers={"User-Agent": UA}, timeout=60)
        r.raise_for_status()
        for q, e in r.json().get("entities", {}).items():
            names = [x["value"] for x in e.get("labels", {}).values()]
            names += [a["value"] for a in e.get("aliases", {}).get("en", [])][:8]
            coord = None
            for c in e.get("claims", {}).get("P625", [])[:1]:
                dv = c["mainsnak"].get("datavalue", {}).get("value", {})
                if "longitude" in dv:
                    coord = [round(dv["longitude"], 4), round(dv["latitude"], 4)]
            out[q] = {"names": list(dict.fromkeys(names)), "coord": coord}
        time.sleep(0.3)
    (DATA / "countries.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote countries.json: {len(out)}")
    # 回填只有国家信息的事件坐标
    f = DATA / "events.json.gz"
    if f.exists():
        ev = json.loads(gzip.decompress(f.read_bytes()))
        n = 0
        for r in ev:
            cs = [out.get(q, {}).get("coord") for q in r.get("countries", [])]
            cs = [c for c in cs if c]
            if not r.get("coord") and cs:
                r["coord"], r["coord_src"] = cs[0], "country"
                n += 1
            for c in cs[1:] if r.get("coord_src") == "country" else cs:
                lst = r.setdefault("coords", [])
                if c not in lst and c != r.get("coord") and len(lst) < 8:
                    lst.append(c)
        write_gz(f, ev)
        print("events geolocated by country centroid:", n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["events", "people", "countries", "all"], default="all")
    ap.add_argument("--cats", default="")
    a = ap.parse_args()
    if a.only in ("events", "all"):
        build_events()
    if a.only in ("people", "all"):
        for cat in PEOPLE_CATEGORIES:
            if not a.cats or cat in a.cats.split(","):
                build_people(cat)
    if a.only in ("countries", "all"):
        build_countries()


if __name__ == "__main__":
    main()
