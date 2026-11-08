"""
生成过渡层事件表 data/transitions.json.gz（说明见 backend/transitions.py）。

规则（全部基于 Wikidata 日期，只采用精确到月或日的日期）：
- inception：快照 s2 中某多边形的主要政权 S 的成立日期 d（P571）满足 s1 < d < s2 年初，且 s1 快照中与它重叠过半的
  多边形都还没有 S 作为强候选 → 在 d 日用 s2 的多边形覆盖 s1。
- dissolution：快照 s1 中某多边形的全部强候选都在 s1 与 s2 之间解散（P576），且之后没有其他强候选 → 在最晚的解散日
  用 s2 的多边形（裁剪到原范围）替换。
- 特殊地位领土：data/territories.json.gz 中每个领土的存在期 = 其 Wikidata 条目及前身链中最早的成立日期起（没有记录
  成立日期的，只在 2011 年 Natural Earth 快照中显示，与原来一致）。
只处理公元 1 年以后、相邻快照间隔 ≥ 2 年的快照对。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config  # noqa: E402
from backend.datafile import read_json  # noqa: E402
from backend.geo import BasemapStore  # noqa: E402
from backend.polity import PolityResolver, alive, lifespan  # noqa: E402
from backend.timeutil import HDate, rec_key  # noqa: E402

EXACT = {"naturalearth", "wiki-title", "capital+name", "name", "dynasty"}


CURATED = [
    {"state": "Q30623", "src": 1930, "fid": 82, "name": "Manchuria", "bases": [1938],
     "label": "1932-03-01–1945-08-18 满洲国（Wikidata Q30623 P571/P576）：1938 年快照把东北并入「大日本帝国」多边形，"
              "这里用 1930 年快照的「Manchuria」范围单独画出（不含 1933 年并入的热河，范围为近似）",
     "source": "Wikidata Q30623 P571/P576；几何 historical-basemaps 1930"},
]


# 主权在历史上变更过的特殊领土：按时期拆成几条记录（名称、主权国、类别随日期变化）。
# 日期取自 Wikidata 各时期条目的 P571（Q1054923 英属香港 1841-01-26–1997-06-30；Q8646 香港特别行政区 1997-07-01 起；
# Q3916279 葡属澳门 1557–1999-12-20；Q14773 澳门特别行政区 1999-12-20 起）。每个时期截止于下一个时期的开始日。
# 几何沿用 Natural Earth 现代范围（香港 1860 年以前只有香港岛、1898 年以前不含新界——范围为近似）。
ERAS = {
    "Q8646": [("Q1054923", "British Hong Kong", "英属香港", "United Kingdom", "hk_uk"),   # 起始日见 ERA_FROM
              ("Q8646", "Hong Kong S.A.R.", "香港", "China", "sar")],
    "Q14773": [("Q3916279", "Portuguese Macau", "葡属澳门", "Portugal", "mo_pt"),
               ("Q14773", "Macao S.A.R", "澳门", "China", "sar")],
}


# 时期起始日的人工修正（每条注明来源）：英军 1841-01-26 占领香港岛（Wikidata P571），但割让以 1842-08-29《南京条约》为准；
# 本地没有 1842–1860（只有香港岛）与 1860–1898（加九龙）的边界，在此之前不单独画出香港
ERA_FROM = {"Q1054923": {"y": 1842, "m": 8, "d": 29, "p": 11}}
GEOM_NOTE = {"Q1054923": "范围为近似：地图用现代香港全境（Natural Earth）。实际 1842–1860 年英国只管治香港岛，1860 年起加九龙半岛南部，"
                         "1898 年起加租借的新界（《展拓香港界址专条》）。"}


def dstr(t):
    return f"{t['y']}-{t.get('m') or 1:02d}-{t.get('d') or 1:02d}"


def main():
    B = BasemapStore()
    B.trans.events, B.trans.terr = [], []        # 生成时只用真实快照
    R = PolityResolver(config.DATA_DIR)
    R.geo = B
    events = []
    ys = [y for y in B.years if y >= 1]
    for s1, s2 in zip(ys, ys[1:]):
        if s2 - s1 < 2:
            continue
        k1, k2 = HDate(s1, 1, 1).key(), HDate(s2, 1, 1).key()
        f1s, f2s = B.features(s1), B.features(s2)
        # inception
        for fid2, f2 in f2s.items():
            c = R.strong(s2, fid2, HDate(s2, 1, 1))
            if not c or c[0]["method"] not in EXACT:
                continue
            S = c[0]["state"]
            d = ERA_FROM.get(S["id"], S.get("from"))
            if not d or (d.get("p") or 0) < 10 or not (k1 < rec_key(d) < k2):
                continue
            g2 = f2["geom"]
            # s1 快照中已经以 S 为候选的多边形覆盖了 g2 的 90% 以上 → 上一张快照已经画出了它，不需要修正
            covered = 0.0
            dd = HDate(d["y"], d.get("m") or 1, d.get("d") or 1)
            for fid1, f1 in f1s.items():
                if f1["geom"].intersects(g2) and any(x["state"]["id"] == S["id"] for x in R.resolve(s1, fid1, dd)):
                    covered += f1["geom"].intersection(g2).area
            if covered >= 0.9 * g2.area:
                continue
            events.append({"base": s1, "src": s2, "kind": "inception", "fid": fid2, "date": d, "state": S["id"],
                           "label": f"{dstr(d)} {S.get('zh') or S.get('en')} 成立（Wikidata {S['id']} P571）；范围取 {s2} 年快照",
                           "source": f"Wikidata {S['id']} P571"})
        # dissolution
        for fid1, f1 in f1s.items():
            c = R.strong(s1, fid1, HDate(s1, 1, 1))
            if not c:
                continue
            ends = []
            for x in c:
                b = x["state"].get("to")
                if b is None:
                    ends = None
                    break
                ends.append((rec_key(b), b, x["state"]))
            if not ends:
                continue
            kb, b, S = max(ends, key=lambda e: e[0])
            if (b.get("p") or 0) < 10 or not (k1 < kb < k2):
                continue
            events.append({"base": s1, "src": s2, "kind": "dissolution", "fid": fid1, "date": b, "state": S["id"],
                           "label": f"{dstr(b)} {S.get('zh') or S.get('en')} 解散（Wikidata {S['id']} P576）；该区域改用 {s2} 年快照",
                           "source": f"Wikidata {S['id']} P576"})
    # 人工指定的几何修正（快照把某政权并入了别的多边形）：几何取自另一张快照的多边形，日期取自 Wikidata
    for c in CURATED:
        S = R.states.get(c["state"])
        f = B.features(c["src"]).get(c["fid"]) if S else None
        if not S or not f or f["props"].get("NAME") != c["name"]:
            print("curated skipped:", c)
            continue
        a, b = S.get("from"), S.get("to")
        for base in c["bases"]:
            d = a if rec_key(a) > HDate(base, 1, 1).key() else {"y": base, "m": 1, "d": 1, "p": 11}
            events.append({"base": base, "src": c["src"], "kind": "inception", "fid": c["fid"], "date": d, "until": b,
                           "state": S["id"], "label": c["label"], "source": c["source"]})
    # 特殊地位领土
    terr = []
    ne_qids = {f["props"].get("QID") for f in B.features(2011).values()}
    for t in read_json(config.DATA_DIR / "territories.json.gz", []):
        chain = [R.states[q] for q in t["chain"] if q in R.states]
        froms = [s["from"] for s in chain if s.get("from")]
        rec = {k: t[k] for k in ("id", "name", "name_zh", "chain", "geom", "src")}
        rec["sov_name"] = t.get("sov")
        if t.get("augment"):
            roc = R.states.get("Q13426199", {})
            rec.update(augment=t["augment"], **{"from": roc.get("to")},
                       label=f"{dstr(roc['to'])} 起：澎湖、金门、马祖并入台湾（中华民国(1912–1949) 在中国大陆的解散日期，Wikidata Q13426199 P576；几何：{t['src']}）")
        elif froms:
            rec["from"] = min(froms, key=rec_key)
            last = chain[-1] if chain else None
            ends = [s.get("to") for s in chain]
            if chain and all(ends):
                rec["to"] = max(ends, key=rec_key)
            rec["label"] = f"{t.get('name_zh') or t['name']}：特殊地位领土（自 {dstr(rec['from'])}）"
        else:
            rec["from"] = {"y": 2011, "m": 1, "d": 1, "p": 11}
            rec["label"] = f"{t.get('name_zh') or t['name']}：Wikidata 未记录成立时间，只在现代显示"
        if t["id"] in ne_qids:
            rec["skip_snaps"] = [2011]   # Natural Earth 2011 快照中本来就是单独的多边形
        if t["id"] in ERAS:
            eras = [(R.states.get(q), en, zh, sov, cat) for q, en, zh, sov, cat in ERAS[t["id"]]]
            if all(e[0] and e[0].get("from") for e in eras):
                for k, (S, en, zh, sov, cat) in enumerate(eras):
                    r2 = {**rec, "name": en, "name_zh": zh, "sov_name": sov, "cat": cat, "from": ERA_FROM.get(S["id"], S["from"])}
                    if S["id"] in GEOM_NOTE:
                        r2["geom_note"] = GEOM_NOTE[S["id"]]
                    r2.pop("to", None)
                    if k + 1 < len(eras):
                        r2["to"] = ERA_FROM.get(eras[k + 1][0]["id"], eras[k + 1][0]["from"])
                    r2["label"] = f"{zh}：{dstr(r2['from'])} 起（Wikidata {S['id']} P571）" + (f"，至 {dstr(r2['to'])}" if r2.get("to") else "")
                    terr.append(r2)
                continue
            print("ERAS skipped (missing dates):", t["id"])
        terr.append(rec)
    # historical-basemaps 从 1650 年快照起就把香港画成单独的「Hong Kong」多边形（早于英国占领）：1842-08-29《南京条约》割让以前，
    # 把它并回包围它的中国多边形（只对含有该多边形的快照生效）
    from shapely.geometry import Point, mapping as _mapping
    for base in B.years:
        fs = B.features(base)
        hk = [f for f in fs.values() if f["props"].get("NAME") == "Hong Kong" and f["geom"].contains(Point(114.17, 22.3))]
        cn = [f for f in fs.values() if f["geom"].contains(Point(113.3, 23.1))]
        if not hk or not cn or base >= 1842:
            continue
        terr.append({"id": "hk_merge", "name": "Hong Kong", "chain": [], "geom": _mapping(hk[0]["geom"]), "src": "historical-basemaps",
                     "augment": cn[0]["props"]["NAME"], "only_snaps": [base], "to": ERA_FROM["Q1054923"],
                     "label": f"{base} 年快照把香港画成单独多边形；1842-08-29（《南京条约》）以前并入「{cn[0]['props']['NAME']}」显示"})
    # 实际控制区（data/curated/control_zones.json，as_polity=true 的作为单独政权多边形，如 1950 年中华民国控制的海南岛）
    from backend import control_zones as CZ
    for z in CZ.load(config.DATA_DIR):
        if not z.get("as_polity"):
            continue
        rec = {"id": z["controller"]["qid"], "name": z["name_en"], "name_zh": z["name_zh"],
               "chain": [z["controller"]["qid"]] if z["controller"].get("qid") else [],
               "geom": z["geom"], "src": "data/curated/control_zones.json", "sov_name": None,
               "cat": z.get("cat") or ("zone_" + z["kind"]),
               "zone": z["id"], "from": CZ.parse(z.get("from"))}
        if z.get("precision"):
            rec["precision"] = z["precision"]
        if z.get("until"):
            rec["to"] = CZ.parse(z["until"], end=True)
        rec["label"] = f"{z['name_zh']}：{z.get('from')} 起" + (f"，至 {z['until']}" if z.get("until") else "") + \
            ("（大致范围）" if z.get("approx") else "") + "（data/curated/control_zones.json）"
        rec["geom_note"] = " ".join(x for x in (z.get("dates_note"), z.get("note"), "范围为近似（大致范围）。" if z.get("approx") else None) if x)
        terr.append(rec)
    out = {"events": events, "territories": terr}
    import gzip
    with gzip.open(config.DATA_DIR / "transitions.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("events:", len(events), "by kind:", {k: sum(e["kind"] == k for e in events) for k in ("inception", "dissolution")},
          "territories:", len(terr))
    for e in events:
        if e["base"] >= 1900:
            print(" ", e["base"], e["label"])


if __name__ == "__main__":
    main()
