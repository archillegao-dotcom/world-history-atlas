"""
特殊地位领土（特别行政区、海外领地、皇家属地、自治领地……）：几何与地位变化。

几何：Natural Earth 1:10m（公有领域）
  - ne_10m_admin_0_countries.geojson：SOVEREIGNT 与 ADMIN 不同的属地、特别行政区等
  - ne_10m_admin_0_map_units.geojson：斯瓦尔巴、扬马延，以及法国海外省（瓜德罗普、马提尼克、法属圭亚那、留尼汪、马约特）
  - 另外：中华民国（台湾）1:10m 范围（含澎湖、金门）+ ne_10m_minor_islands 中包含 Wikidata 马祖列岛（Q609255）坐标的岛屿，
    用于 1949-12-07 以后把澎湖、金门、马祖画入台湾（historical-basemaps 的快照里没有这些小岛）。
地位：Wikidata 中该领土条目及其「取代了」(P1365) 链上的前身（如 香港特别行政区 ← 英属香港），各自的成立/解散日期由
build_states.py 从 Wikidata 读取（本脚本把这些 QID 写入 data/territory_qids.json 供 build_states.py 一并抓取）。

输出：data/territories.json.gz  [{id, name_zh, sov, geom(GeoJSON, 简化), chain:[QID...], kind}]
运行顺序：python tools/build_territories.py --qids  → python tools/build_states.py → python tools/build_territories.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wdsparql import DATA, cached, qid, v, write_gz  # noqa: E402

RAW = DATA / "basemaps_raw"
# 收录的属地（Natural Earth ADMIN / GEOUNIT 名）。不收录：无人冰原、争议礁滩、军事基地、南极洲（不是「特殊行政地位」）。
COUNTRY_UNITS = [
    "Hong Kong S.A.R.", "Macao S.A.R", "Greenland", "Faroe Islands", "Aland", "Puerto Rico", "Guam",
    "Northern Mariana Islands", "American Samoa", "United States Virgin Islands", "Jersey", "Guernsey", "Isle of Man",
    "Gibraltar", "Bermuda", "Cayman Islands", "British Virgin Islands", "Anguilla", "Montserrat",
    "Turks and Caicos Islands", "Falkland Islands", "Saint Helena", "Pitcairn Islands", "South Georgia and the Islands",
    "British Indian Ocean Territory", "Akrotiri Sovereign Base Area", "Dhekelia Sovereign Base Area",
    "New Caledonia", "French Polynesia", "Wallis and Futuna", "Saint Pierre and Miquelon", "Saint Barthelemy",
    "Saint Martin", "French Southern and Antarctic Lands", "Clipperton Island", "Aruba", "Curaçao", "Sint Maarten",
    "Cook Islands", "Niue", "Norfolk Island", "Indian Ocean Territories", "Heard Island and McDonald Islands",
    "Western Sahara",
]
MAP_UNITS = ["Svalbard", "Jan Mayen", "French Guiana", "Guadeloupe", "Martinique", "Reunion", "Mayotte"]
# Wikidata 中缺少 P1365 链接、或链接到不相干前身的条目：人工指定前身链（QID 均为 Wikidata 条目）
CHAIN_OVERRIDE = {
    "Q8646": ["Q8646", "Q1054923"],      # 香港特别行政区 ← 英属香港（1841–1997）
    "Q14773": ["Q14773", "Q3916279"],    # 澳门特别行政区 ← 葡属澳门（1557–1999）
    "Q129003": ["Q129003"],              # 法属南部和南极领地：Wikidata P1365 指向法属马达加斯加，不作为前身
}
MATSU_QID, MATSU_CO = "Q609255", (119.9333, 26.15)   # Wikidata P625
SIMPLIFY = 0.005


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))["features"]


def units():
    out = []
    for f in load("ne_10m_admin_0_countries.geojson"):
        p = f["properties"]
        if p["ADMIN"] in COUNTRY_UNITS:
            out.append((p["ADMIN"], p.get("WIKIDATAID"), p.get("NAME_ZH"), p["SOVEREIGNT"], f["geometry"]))
    for f in load("ne_10m_admin_0_map_units.geojson"):
        p = f["properties"]
        if p["GEOUNIT"] in MAP_UNITS:
            out.append((p["GEOUNIT"], p.get("WIKIDATAID"), p.get("NAME_ZH"), p["SOVEREIGNT"], f["geometry"]))
    return out


def chains(qids):
    """每个领土的 P1365 前身链（最多 3 层）。"""
    vals = " ".join(f"wd:{q}" for q in qids)
    rows = cached("terr_pred", f"SELECT ?t ?p1 ?p2 ?p3 WHERE {{ VALUES ?t {{ {vals} }} "
                               "OPTIONAL { ?t wdt:P1365 ?p1. OPTIONAL { ?p1 wdt:P1365 ?p2. OPTIONAL { ?p2 wdt:P1365 ?p3. } } } }")
    ch = {q: [q] for q in qids}
    for b in rows:
        t = qid(v(b, "t"))
        for k in ("p1", "p2", "p3"):
            x = v(b, k)
            if x and qid(x) not in ch[t]:
                ch[t].append(qid(x))
    ch.update({k: list(v_) for k, v_ in CHAIN_OVERRIDE.items() if k in ch})
    return ch


def taiwan_islands():
    tw = [shape(f["geometry"]) for f in load("ne_10m_admin_0_countries.geojson") if f["properties"]["ADM0_A3"] == "TWN"]
    mp = Point(*MATSU_CO)
    isl = [shape(f["geometry"]) for f in load("ne_10m_minor_islands.geojson") if shape(f["geometry"]).distance(mp) < 0.06]
    return unary_union(tw + isl).simplify(0.002)


def main():
    us = units()
    qids = [u[1] for u in us if u[1]]
    ch = chains(qids)
    if "--qids" in sys.argv:
        allq = sorted({x for c in ch.values() for x in c})
        (DATA / "territory_qids.json").write_text(json.dumps(allq), encoding="utf-8")
        print("territory qids:", len(allq))
        return
    recs = []
    for name, q, zh, sov, g in us:
        geom = shape(g).simplify(SIMPLIFY, preserve_topology=True)
        recs.append({"id": q, "name": name, "name_zh": zh, "sov": sov, "chain": ch.get(q, [q]),
                     "geom": mapping(geom), "src": "Natural Earth 1:10m admin-0"})
    recs.append({"id": "TW_ISLANDS", "name": "Taiwan (incl. Penghu, Kinmen, Matsu)", "name_zh": "台湾（含澎湖、金门、马祖）",
                 "sov": None, "chain": ["Q865"], "geom": mapping(taiwan_islands()), "augment": "Taiwan",
                 "src": "Natural Earth 1:10m admin-0 TWN + ne_10m_minor_islands（马祖：含 Wikidata Q609255 坐标的岛屿）"})
    write_gz(DATA / "territories.json.gz", recs)
    print("territories:", len(recs))


if __name__ == "__main__":
    main()
