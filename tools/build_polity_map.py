#!/usr/bin/env python3
"""
地图政权（historical-basemaps 多边形，只有英文名）→ Wikidata 政权 QID 候选列表。

对每张快照（时期 [本快照年份, 下一张快照年份)）的每个多边形，收集候选：
  1. 名称匹配（score 100+）：NAME / ABBREVN 与政权英文名、英文别名（规范化后）相同，
     或 polity_names.json 中经英文维基同名条目得到的 QID（score 120）；
  2. 首都落在多边形内（score 50+）：政权的某个首都（P36）坐标在多边形内，且该首都声明的起止时间
     （没有限定时用政权存在期）与这一时期重叠；
  3. 政权自身坐标（P625）落在多边形内（score 30+）。
  所有候选都要求政权存在期与该时期重叠（前后各放宽 30 年，因为快照是近似的）。
  同类候选里知名度（sitelinks）高、名称相似的排前面。
运行时（backend/polity.py）再按所选日期筛出「当时存在」的候选。
输出 data/polity_map.json.gz：{快照年份: {fid: [[qid, 方法, 分数], ...]}}
"""
from __future__ import annotations

import gzip
import json
import math
import re
import sys
from pathlib import Path

from shapely import STRtree
from shapely.geometry import Point, shape

from wdsparql import DATA, write_gz

SLACK = 30

# historical-basemaps 中描述性的区域名 → 对应政权的英文名（只收录含义明确的少数几个；仍需与
# Wikidata 政权的英文名/别名匹配，且存在期与快照重叠，才会成为候选）
NAME_ALIASES = {
    "English territory": ["Kingdom of England"],
    "Chinese warlords": ["Republic of China"],
    # historical-basemaps 1920/1930 快照把中国本部标为「Chinese Warlords」（大写 W），同样对应中华民国
    "Chinese Warlords": ["Republic of China"],
    # 满洲：1932-03-01 之前属中华民国，1932–1945 为满洲国（存在期过滤保证各自只在其存在期成为候选）
    "Manchuria": ["Republic of China", "Manchukuo"],
    "Castile": ["Crown of Castile"],
    "Aragón": ["Crown of Aragon"],
    "Shogun Japan (Kamakura)": ["Kamakura shogunate"],
    "Britany": ["Duchy of Brittany"],
    "Mamluke Sultanate": ["Mamluk Sultanate"],
    # 1611–1721 年间的瑞典（存在期过滤保证只在这一时期成为候选）
    "Sweden": ["Swedish Empire"],
    "Spain": ["Spanish Empire"],
    # 以下按英文维基条目名在 Wikidata 中查得 QID（存在期过滤保证各自只在其存在期成为候选）
    "Japan": ["Q1154406", "Q205662", "Q736839"],                       # 室町（足利）幕府 1336–1573、江户幕府 1603–1867、镰仓幕府
    "Shogun Japan (Kamakura)": ["Kamakura shogunate", "Q1154406"],      # 1400 年快照仍标「镰仓」：1336 年以后为室町幕府
    "Japan (Warring States)": ["Q1154406", "Q11634225", "Q205662"],    # 室町幕府（至 1573）、丰臣政权、江户幕府
    "Tibet": ["Q126416", "Q729540", "Q17500081", "Q2444884"],          # 帕木竹巴 1354–1618、藏巴汗 1565–1642、甘丹颇章 1642–1959、西藏(1912–1951)
    "Tufan Empire": ["Q2431480"],                                       # 吐蕃 618–842
    "Mexihcah (Triple Alliance)": ["Q2608489"],                         # 阿兹特克帝国
    "Viceroyalty of New Spain": ["Q170603"],
    "Viceroyalty of Peru": ["Q211435"],
    "Viceroyalty of New Granada": ["Q8965"],
    "Algiers": ["Q3045696"],                                            # 阿尔及尔摄政国 1516–1830
    "Algeria": ["Q218272"], "Algeria (FR)": ["Q218272"], "Algeria (France)": ["Q218272"],   # 法属阿尔及利亚 1830–1962
    "French West Africa": ["Q210682"], "French Equatorial Africa": ["Q271894"],
    "Rupert's Land": ["Q738395"],
    "Khazars": ["Q2090473"],                                            # 可萨汗国
    "Cuman-Kipchak confederation": ["Q1122052"],
    "Quazaq Khanate": ["Q1433867"],                                     # 哈萨克汗国
    "Luisiana": ["Q658054"], "Louisiana": ["Q658054"],                  # 法属路易斯安那
    "New France": ["Q170604"],
    "Dutch East Indies": ["Q188161"],
    "Portuguese India": ["Q323904"],
}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"^(the |kingdom of |empire of |republic of |sultanate of |principality of |duchy of )", "", s)
    s2 = re.sub(r"( empire| kingdom| sultanate| dynasty| republic| caliphate| khanate)$", "", s.strip())
    # 去掉后缀后只剩泛泛的词（如 United Kingdom → united）时保留原名，避免 United States 与 United Kingdom 混淆
    if s2.strip() not in ("united", "holy", "great", "new", "old", "first", "second", "third"):
        s = s2
    return re.sub(r"[^a-z0-9]+", "", s)


def y(t):
    return t["y"] if t else None


def overlaps(a0, a1, b0, b1):
    """区间 [a0,a1] 与 [b0,b1] 是否重叠；None 表示无界。"""
    return (a1 is None or b0 is None or a1 >= b0 - SLACK) and (a0 is None or b1 is None or a0 <= b1 + SLACK)


def main():
    states = json.loads(gzip.decompress((DATA / "states.json.gz").read_bytes()))
    pn = json.loads((DATA / "polity_names.json").read_text(encoding="utf-8"))
    idx = json.loads((DATA / "basemaps" / "index.json").read_text(encoding="utf-8"))
    years = [x["year"] for x in idx]
    byname = {}
    for s in states:
        for n in [s.get("en")] + s.get("aliases", []):
            if n:
                byname.setdefault(norm(n), []).append(s)
    # 首都点 & 自身坐标点
    cap_pts, cap_info = [], []
    for s in states:
        for c in s.get("capitals", []):
            if c.get("coord"):
                f0 = y(c.get("from")) if c.get("from") else y(s.get("from"))
                t0 = y(c.get("to")) if c.get("to") else y(s.get("to"))
                cap_pts.append(Point(c["coord"]))
                cap_info.append((s, f0, t0, "capital"))
        if s.get("coord"):
            cap_pts.append(Point(s["coord"]))
            cap_info.append((s, y(s.get("from")), y(s.get("to")), "coord"))
    tree = STRtree(cap_pts)
    sid = {s["id"]: s for s in states}
    out = {}
    stat = {"features": 0, "with_candidates": 0}
    for i, ent in enumerate(idx):
        snap = ent["year"]
        nxt = years[i + 1] if i + 1 < len(years) else 2100
        fc = json.loads(gzip.decompress((DATA / "basemaps" / ent["file"]).read_bytes()))
        m = {}
        for ft in fc["features"]:
            p = ft["properties"]
            stat["features"] += 1
            g = shape(ft["geometry"])
            cands = {}

            def add(s, method, score):
                if s["id"] not in cands or cands[s["id"]][2] < score:
                    cands[s["id"]] = [s["id"], method, round(score, 1)]

            names = {norm(p.get("NAME"))} if p.get("NAME") else set()
            ab = norm(p.get("ABBREVN"))
            if len(ab) >= 5:  # 缩写太短（如 S.K.）容易误配（斯洛伐克 SK），不用
                names.add(ab)
            names.discard("")
            names |= {norm(x) for x in NAME_ALIASES.get(p.get("NAME"), []) if not re.fullmatch(r"Q\d+", x)}
            for x in NAME_ALIASES.get(p.get("NAME"), []):
                if re.fullmatch(r"Q\d+", x) and x in sid:
                    s_ = sid[x]
                    if overlaps(y(s_.get("from")), y(s_.get("to")), snap, nxt):
                        add(s_, "name", 110 + math.log10(s_["sl"] + 1))
            # Natural Earth 快照自带 QID
            if p.get("QID"):
                cands[p["QID"]] = [p["QID"], "naturalearth", 200]
            rec = pn.get(p.get("NAME") or "", {}) or {}
            if rec.get("qid") and rec["qid"] in sid:
                s = sid[rec["qid"]]
                if overlaps(y(s.get("from")), y(s.get("to")), snap, nxt):
                    add(s, "wiki-title", 120 + math.log10(s["sl"] + 1))
            for n in names:
                for s in byname.get(n, []):
                    if overlaps(y(s.get("from")), y(s.get("to")), snap, nxt):
                        add(s, "name", 100 + math.log10(s["sl"] + 1))
            for j in tree.query(g, predicate="contains"):
                s, f0, t0, kind = cap_info[j]
                if overlaps(f0, t0, snap, nxt):
                    sim = 10 if any(n and n in norm(s.get("en")) for n in names) else 0
                    add(s, kind + ("+name" if sim else ""), (50 if kind == "capital" else 30) + sim + 3 * math.log10(s["sl"] + 1))
            lst = sorted(cands.values(), key=lambda c: -c[2])[:10]
            if lst:
                stat["with_candidates"] += 1
                m[str(p["fid"])] = lst
        out[str(snap)] = m
        print(snap, len(m), "/", len(fc["features"]), flush=True)
    write_gz(DATA / "polity_map.json.gz", out)
    print(stat)


if __name__ == "__main__":
    main()
