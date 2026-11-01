#!/usr/bin/env python3
"""
构建两份地点数据（来源：Wikidata，经 QLever SPARQL）：

1) data/cities.json.gz —— 地图「主要城市」图层
   - 城市：P31 属于 city(Q515) / ancient city(Q15661340) / capital(Q5119) 及其子类，有坐标，sitelinks ≥ 40；
   - 存在时间：P571 建立时间、P576 废弃/解散时间（有则用；没有建立时间的城市只在 1800 年后显示——
     这是保守做法，避免把现代城市画到古代地图上）；
   - 历史名称：P1448 官方名称及其 P580/P582 起止限定（原文语言，如 Constantinople 期间的名称）；
   - 首都：P1376「首都所属」及其起止限定；目标是国家/历史国家/帝国等时记为国家首都；
   - 排名：sitelinks 与人口 P1082（取最大值）。
2) data/gazetteer.json.gz —— 英文维基条目名 -> 坐标/QID/中文名，用于把「每日新闻」条目中的
   链接（如 [[Madagascar]]、[[Fairfield, California]]）定位到地图上。
"""
from __future__ import annotations

import math

from wdsparql import DATA, cached, parse_point, parse_time, pick_zh, qid, simplifier, v, write_gz

CITY_MIN_SL = 40
ANCIENT_MIN_SL = 12
GAZ_MIN_SL = 25
# 视为「国家级」首都的目标类型（国家、主权国家、历史国家、帝国、王国……）
STATE_TYPES = "wd:Q6256 wd:Q3624078 wd:Q3024240 wd:Q7275 wd:Q48349 wd:Q417175 wd:Q1250464 wd:Q133442 wd:Q10711424 wd:Q1520223"
RANK = {"http://wikiba.se/ontology#PreferredRank": 0, "http://wikiba.se/ontology#NormalRank": 1}


def build_cities():
    # 现代/一般城市门槛高；古城（ancient city，如咸阳、长安、乌尔）门槛低，否则古代地图上几乎没有城市
    core = (f"{{ VALUES ?root {{ wd:Q515 wd:Q5119 }} ?c wdt:P31/wdt:P279* ?root; wikibase:sitelinks ?sl. FILTER(?sl >= {CITY_MIN_SL}) }} "
            f"UNION {{ ?c wdt:P31/wdt:P279* wd:Q15661340; wikibase:sitelinks ?sl. FILTER(?sl >= {ANCIENT_MIN_SL}) }} "
            f"?c wdt:P625 ?coord0.")
    q = lambda name, sel, body: cached(name, f"SELECT DISTINCT {sel} WHERE {{ {core} {body} }}")
    recs: dict[str, dict] = {}
    for b in q("city_core", "?c ?sl ?coord0", ""):
        pt = parse_point(v(b, "coord0"))
        if pt:
            recs.setdefault(qid(v(b, "c")), {"id": qid(v(b, "c")), "sl": int(v(b, "sl")), "coord": pt})
    for b in q("city_pop", "?c ?pop", "?c wdt:P1082 ?pop."):
        r = recs.get(qid(v(b, "c")))
        try:
            pop = int(float(v(b, "pop")))
        except (TypeError, ValueError):
            continue
        if r and pop > r.get("pop", 0):
            r["pop"] = pop
    for prop, fld in (("P571", "from"), ("P576", "to")):
        for b in q(f"city_{prop}", "?c ?t ?tp ?rank",
                   f"?c p:{prop} ?st. ?st wikibase:rank ?rank; psv:{prop} ?tv. ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp."):
            r = recs.get(qid(v(b, "c")))
            t = parse_time(v(b, "t"), v(b, "tp"))
            if not r or not t or v(b, "rank") not in RANK:
                continue
            # 建立时间取最早，废弃时间取最晚（保守：让城市显示的时间范围尽量覆盖有记录的存在期）
            key = (t["y"], t["m"], t["d"])
            old = r.get(fld)
            if not old or (key < (old["y"], old["m"], old["d"]) if fld == "from" else key > (old["y"], old["m"], old["d"])):
                r[fld] = t
    # 历史官方名称（带起止时间的才有意义）
    for b in q("city_names", "?c ?name ?s ?sp ?e ?ep",
               "?c p:P1448 ?st. ?st ps:P1448 ?name. "
               "OPTIONAL { ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s; wikibase:timePrecision ?sp. } "
               "OPTIONAL { ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e; wikibase:timePrecision ?ep. }"):
        r = recs.get(qid(v(b, "c")))
        if not r or not (b.get("s") or b.get("e")):
            continue
        lang = b["name"].get("xml:lang") or ""
        nm = simplifier()(v(b, "name")) if lang.startswith("zh") else v(b, "name")
        r.setdefault("names", []).append({"name": nm, "lang": lang,
                                          "from": parse_time(v(b, "s"), v(b, "sp")),
                                          "to": parse_time(v(b, "e"), v(b, "ep"))})
    # 首都（国家级）
    for b in q("city_capital", "?c ?of ?s ?sp ?e ?ep",
               f"?c p:P1376 ?st. ?st ps:P1376 ?of. VALUES ?stype {{ {STATE_TYPES} }} ?of wdt:P31 ?stype. "
               "OPTIONAL { ?st pqv:P580 ?sv. ?sv wikibase:timeValue ?s; wikibase:timePrecision ?sp. } "
               "OPTIONAL { ?st pqv:P582 ?ev. ?ev wikibase:timeValue ?e; wikibase:timePrecision ?ep. }"):
        r = recs.get(qid(v(b, "c")))
        if r:
            cap = {"of": qid(v(b, "of")), "from": parse_time(v(b, "s"), v(b, "sp")), "to": parse_time(v(b, "e"), v(b, "ep"))}
            if cap not in r.setdefault("capital", []):
                r["capital"].append(cap)
    # 首都所属国家本身的存在时间（首都声明没有起止限定时，用国家的存在期来判断）
    ofs = sorted({c["of"] for r in recs.values() for c in r.get("capital", [])})
    states: dict[str, dict] = {}
    for k in range(0, len(ofs), 400):
        vals = " ".join(f"wd:{x}" for x in ofs[k:k + 400])
        for b in cached(f"state_life_{k}", f"""SELECT ?s ?prop ?t ?tp WHERE {{ VALUES ?s {{ {vals} }}
              VALUES ?prop {{ p:P571 p:P576 }} ?s ?prop ?st. ?st wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank)
              {{ ?st psv:P571 ?tv }} UNION {{ ?st psv:P576 ?tv }} ?tv wikibase:timeValue ?t; wikibase:timePrecision ?tp. }}"""):
            t = parse_time(v(b, "t"), v(b, "tp"))
            if t:
                fld = "from" if v(b, "prop").endswith("P571") else "to"
                s = states.setdefault(qid(v(b, "s")), {})
                if fld not in s or (t["y"] < s[fld]["y"] if fld == "from" else t["y"] > s[fld]["y"]):
                    s[fld] = t
    for r in recs.values():
        for c in r.get("capital", []):
            st = states.get(c["of"], {})
            c["state_from"], c["state_to"] = st.get("from"), st.get("to")
    # 标签
    t2s = simplifier()
    labels: dict[str, dict] = {}
    for b in q("city_labels", "?c ?l", '?c rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans","zh-hant","zh-tw","en"))'):
        labels.setdefault(qid(v(b, "c")), {})[b["l"].get("xml:lang")] = b["l"]["value"]
    for b in q("city_enwiki", "?c ?w", "?w schema:about ?c; schema:isPartOf <https://en.wikipedia.org/>."):
        r = recs.get(qid(v(b, "c")))
        if r:
            r["enwiki"] = v(b, "w")
    for b in q("city_zhwiki", "?c ?w", "?w schema:about ?c; schema:isPartOf <https://zh.wikipedia.org/>."):
        r = recs.get(qid(v(b, "c")))
        if r:
            r["zhwiki"] = v(b, "w")
    for qq, r in recs.items():
        ls = labels.get(qq, {})
        zh, _ = pick_zh(ls)
        r["zh"] = t2s(zh) if zh else None
        r["en"] = ls.get("en")
        # 综合排名分：sitelinks 为主，人口为辅（对数）
        r["score"] = round(r["sl"] + 6 * math.log10(max(r.get("pop", 0), 1)), 1)
    out = sorted((r for r in recs.values() if r.get("zh") or r.get("en")), key=lambda r: -r["score"])
    write_gz(DATA / "cities.json.gz", out)


def build_gazetteer():
    core = (f"VALUES ?root {{ wd:Q486972 wd:Q56061 wd:Q6256 wd:Q3024240 wd:Q3624078 }} "
            f"?c wdt:P31/wdt:P279* ?root; wikibase:sitelinks ?sl. FILTER(?sl >= {GAZ_MIN_SL}) ?c wdt:P625 ?coord. "
            f"?w schema:about ?c; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?title.")
    rows = cached("gaz_core", f"SELECT DISTINCT ?c ?sl ?coord ?title WHERE {{ {core} }}")
    zh = {}
    t2s = simplifier()
    lab = cached("gaz_zh", f'SELECT DISTINCT ?c ?l WHERE {{ {core} ?c rdfs:label ?l. FILTER(LANG(?l) IN ("zh","zh-cn","zh-hans")) }}')
    for b in lab:
        zh.setdefault(qid(v(b, "c")), {})[b["l"]["xml:lang"]] = b["l"]["value"]
    # 国家（用于标注「国家」级定位）
    countries = {qid(v(b, "c")) for b in cached("gaz_countries", f"SELECT DISTINCT ?c WHERE {{ {core} VALUES ?ct {{ wd:Q6256 wd:Q3624078 }} ?c wdt:P31 ?ct. }}")}
    out = {}
    for b in rows:
        q, pt = qid(v(b, "c")), parse_point(v(b, "coord"))
        if not pt:
            continue
        title = v(b, "title")
        z, _ = pick_zh(zh.get(q, {}))
        rec = [pt[0], pt[1], q, t2s(z) if z else None, int(v(b, "sl")), 1 if q in countries else 0]
        if title not in out or rec[4] > out[title][4]:
            out[title] = rec
    write_gz(DATA / "gazetteer.json.gz", out)


if __name__ == "__main__":
    import sys
    if "cities" in sys.argv[1:] or len(sys.argv) == 1:
        build_cities()
    if "gazetteer" in sys.argv[1:] or len(sys.argv) == 1:
        build_gazetteer()
