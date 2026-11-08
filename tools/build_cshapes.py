#!/usr/bin/env python3
"""
CShapes 2.0（ETH Zürich ICR，Schvitz et al. 2022，CC BY-NC-SA 4.0）→ data/cshapes.json.gz
1886-01-01 至 2019-12-31 的底图改用 CShapes：每一行是一个国家/殖民地在一段时间内不变的边界（精确到日，法理边界）。
输入：data/cshapes_raw/CShapes-2.0.csv（几何，WKT）+ cshapes_2_gw.topojson（R 包内附，含 status/owner）
      data/curated/cshapes_periods.json（gwcode → 各时期的 Wikidata 政权）
      data/basemaps_raw/ne_10m_admin_0_countries.geojson（2019 年的 CShapes 行 → Natural Earth QID；补微型国家/小岛国）
输出：rows[{i, gw, name, status, owner, from, to(不含), cap, capname, b_def, geom}], gw{gw: {periods, names, ne}}, extras[...]
"""
from __future__ import annotations
import csv, json, re, sys, datetime
from pathlib import Path
from shapely import wkt, make_valid
from shapely.geometry import mapping, shape, Point
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.datafile import read_json  # noqa
RAW = ROOT / "data" / "cshapes_raw"
csv.field_size_limit(1 << 30)

def ymd(s):  # "1886-01-01" -> 18860101
    y, m, d = s.split("-"); return int(y) * 10000 + int(m) * 100 + int(d)

def plus1(s):
    d = datetime.date.fromisoformat(s) + datetime.timedelta(days=1); return d.year * 10000 + d.month * 100 + d.day

def rnd(g, nd=3):
    def r(c):
        if isinstance(c[0], (int, float)): return [round(c[0], nd), round(c[1], nd)]
        return [r(x) for x in c]
    m = mapping(g); return {"type": m["type"], "coordinates": r(m["coordinates"])}

def simp(g):
    a = g.area
    tol = 0.005 if a > 50 else 0.002 if a > 1 else 0.0005
    s = make_valid(g.simplify(tol, preserve_topology=True))
    return s if not s.is_empty else g

def main():
    topo = json.load(open(RAW / "gw.topojson"))
    meta = {}
    for g in list(topo["objects"].values())[0]["geometries"]:
        p = g["properties"]; meta[(p["gwcode"], p["start"])] = p
    rows = []
    for r in csv.DictReader(open(RAW / "CShapes-2.0.csv", encoding="utf-8")):
        gw = int(r["gwcode"]); st = f'{int(r["gwsyear"]):04d}-{int(r["gwsmonth"]):02d}-{int(r["gwsday"]):02d}'
        en = f'{int(r["gweyear"]):04d}-{int(r["gwemonth"]):02d}-{int(r["gweday"]):02d}'
        m = meta.get((gw, st))
        if m is None:
            print("no meta", gw, st, r["cntry_name"]); continue
        g = make_valid(wkt.loads(r["the_geom"].split(";", 1)[1]))
        rows.append({"i": len(rows), "gw": gw, "name": r["cntry_name"], "status": m["status"], "owner": int(m["owner"]) if str(m["owner"]).isdigit() else None,
                     "from": ymd(st), "to": plus1(m["end"]) if m["end"] < "2019-12-31" else None,
                     "cap": [round(float(r["caplong"]), 4), round(float(r["caplat"]), 4)], "capname": r["capname"], "b_def": m.get("b_def"),
                     "_g": g})
    print("rows", len(rows))
    # ---- 名称匹配候选
    states = read_json(ROOT / "data" / "states.json.gz")
    by = {}
    for s in states:
        for n in [s.get("en")] + (s.get("aliases") or []):
            if n: by.setdefault(n.lower(), set()).add(s["id"])
    def variants(name):
        out = {name}
        for part in re.split(r"[/()]", name):
            part = part.strip(" ,")
            if part: out.add(part)
        if ", " in name:   # "Korea, Republic of" → "Republic of Korea"
            a, b = name.split(", ", 1); out.add(f"{b} {a}")
        return out
    # ---- Natural Earth：2019 年的行 → QID
    ne = [f for f in json.load(open(ROOT / "data" / "basemaps_raw" / "ne_10m_admin_0_countries.geojson"))["features"]]
    neg = [(shape(f["geometry"]), f["properties"]) for f in ne]
    per = json.load(open(ROOT / "data" / "curated" / "cshapes_periods.json"))
    gwinfo = {}
    for r in rows:
        gi = gwinfo.setdefault(r["gw"], {"names": set(), "periods": [], "ne": None})
        for v in variants(r["name"]):
            gi["names"] |= by.get(v.lower(), set())
        if r["to"] is None:
            rg = r["_g"]
            best = max(((g.intersection(rg).area if g.intersects(rg) else 0, p) for g, p in neg), key=lambda x: x[0])
            if best[0] > 0.3 * min(rg.area, 1e9) and best[1].get("WIKIDATAID"):
                gi["ne"] = [best[1]["WIKIDATAID"], r["from"]]
    for gw, lst in per["periods"].items():
        gwinfo.setdefault(int(gw), {"names": set(), "periods": [], "ne": None})["periods"] = [[ymd(a), ymd(b) if b else None, q] for a, b, q in lst]
    used_ne = set()
    for gi in gwinfo.values():
        gi["names"] = sorted(gi["names"])
        if gi["ne"]: used_ne.add(gi["ne"][0])
        for p in gi["periods"]: used_ne.add(p[2])
    # ---- 微型国家与小岛国：Natural Earth 1:10m 有、CShapes 没有的主权国家
    sdict = {s["id"]: s for s in states}
    extras = []
    for g, p in neg:
        q = p.get("WIKIDATAID")
        if not q or q in used_ne or p.get("TYPE") not in ("Sovereign country", "Country", "Sovereignty"): continue
        if p.get("SOVEREIGNT") != p.get("ADMIN"): continue
        if g.area > 0.05 and any(r["to"] is None and r["_g"].intersects(g) and r["_g"].intersection(g).area > 0.3 * g.area for r in rows):
            continue   # 已被 CShapes 覆盖（如北塞浦路斯、索马里兰：事实政权，CShapes 按法理边界不单列）
        s = sdict.get(q) or {}
        f = s.get("from")
        a = max(18860101, f["y"] * 10000 + (f.get("m") or 1) * 100 + (f.get("d") or 1)) if f else None
        extras.append({"qid": q, "name": p["ADMIN"], "name_zh": p.get("NAME_ZH"), "from": a, "to": None, "_g": make_valid(g),
                       "src": "Natural Earth 1:10m admin-0", "from_src": f"Wikidata {q} P571" if f else "未记录"})
    # 满洲国（1932-03-01 – 1945-08-18）：CShapes 按法理边界把东北算作中国（其编码规则不记录未获承认、后被撤销的领土变更，
    # 原文举例即日本占领满洲）。这里叠加 historical-basemaps 1930 年快照的「Manchuria」范围（不含 1933 年并入的热河，范围为近似）。
    import gzip as _gz
    hb = json.loads(_gz.decompress((ROOT / "data" / "basemaps" / "1930.geojson.gz").read_bytes()))
    mg = [shape(f["geometry"]) for f in hb["features"] if f["properties"].get("NAME") == "Manchuria"]
    if mg:
        # v0.6.2：1930 年「Manchuria」多边形没有盖满 CShapes 的中国东北（黑河、三江、图们江一带留下中华民国碎块），
        # 并上 Natural Earth 今黑龙江、吉林、辽宁三省；1933-03-04 起再并上热河（原来是单独的「满洲国（热河省）」区域，
        # 地图上出现两个满洲国）。热河范围沿用 zones_asia_ww2.py 的近似折线。
        ne1 = json.loads((ROOT / "data" / "basemaps_raw" / "ne_10m_admin_1_states_provinces.geojson").read_text(encoding="utf-8"))["features"]
        ne_ = [shape(f["geometry"]) for f in ne1 if f["properties"].get("iso_3166_2") in ("CN-HL", "CN-JL", "CN-LN")]
        from shapely.geometry import box as _box
        # 兴安南省一带（今通辽、赤峰北部，1932 年起属满洲国兴安省；近似矩形，与中国 CShapes 求交前的补块）
        base = make_valid(unary_union(mg + [make_valid(g) for g in ne_] + [_box(119.9, 43.5, 121.8, 44.5)]))
        from shapely.geometry import Polygon as _Poly
        jehol = _Poly([[116.4, 41.0], [117.4, 40.6], [118.5, 40.2], [119.7, 40.1], [120.4, 40.6], [121.6, 41.5], [121.0, 42.6],
                       [120.4, 43.5], [119.5, 44.6], [118.0, 44.8], [117.2, 44.0], [116.5, 43.0], [116.0, 42.0]])
        src = "historical-basemaps 1930「Manchuria」∪ Natural Earth 黑龙江/吉林/辽宁（近似）"
        extras.append({"qid": "Q30623", "name": "Manchukuo", "name_zh": "满洲国", "from": 19320301, "to": 19330304, "_g": base,
                       "approx": True, "src": src, "from_src": "Wikidata Q30623 P571/P576"})
        extras.append({"qid": "Q30623", "name": "Manchukuo", "name_zh": "满洲国", "from": 19330304, "to": 19450819,
                       "_g": make_valid(unary_union([base, jehol, _box(119.9, 42.5, 121.8, 43.5)])), "approx": True, "src": src + " ∪ 热河（1933-03-04 起，近似）",
                       "from_src": "Wikidata Q30623 P571/P576；热河：https://en.wikipedia.org/wiki/Battle_of_Rehe"})
    # CShapes（沿用 Gleditsch–Ward 名单）把斯洛文尼亚、克罗地亚、波黑的独立都记为 1992-04-27（南联盟成立日）。
    # 国际通行说法：斯、克两国独立宣言 1991-06-25，三个月暂停期结束后 1991-10-08 生效；波黑 1992-03-03 宣布独立、1992-04-06 获欧共体承认。
    # 这里用 CShapes 1992-04-27 起的边界提前显示，期间从「南斯拉夫」中切出。
    EARLY = [(349, "Q215", "Slovenia", "斯洛文尼亚", 19911008, "https://en.wikipedia.org/wiki/Ten-Day_War"),
             (344, "Q224", "Croatia", "克罗地亚", 19911008, "https://en.wikipedia.org/wiki/Independence_Day_(Croatia)"),
             (346, "Q225", "Bosnia and Herzegovina", "波斯尼亚和黑塞哥维那", 19920406, "https://en.wikipedia.org/wiki/Bosnia_and_Herzegovina#Bosnian_War")]
    for gwc, q, nm, zh, a, src in EARLY:
        r0 = min((r for r in rows if r["gw"] == gwc), key=lambda r: r["from"])
        extras.append({"qid": q, "name": nm, "name_zh": zh, "from": a, "to": r0["from"], "_g": r0["_g"], "src": "CShapes 2.0（" + str(r0["from"]) + " 起的边界）", "from_src": src})
    for e in extras:
        if e["qid"] == "Q702":   # 密克罗尼西亚联邦：Wikidata P571 为 1947（托管地设立），独立为 1986-11-03（Compact of Free Association 生效）
            e["from"] = 19861103; e["from_src"] = "https://en.wikipedia.org/wiki/Federated_States_of_Micronesia"
    print("extras", len(extras), [e["name"] for e in extras])
    out = {"source": "CShapes 2.0 (Schvitz et al. 2022, J. Conflict Resolution 66(1):144–61), ETH Zürich ICR, CC BY-NC-SA 4.0; https://icr.ethz.ch/data/cshapes/",
           "rows": [], "gw": {str(k): v for k, v in gwinfo.items()}, "extras": []}
    for r in rows:
        g = r.pop("_g"); r["geom"] = rnd(simp(g)); out["rows"].append(r)
    for e in extras:
        g = e.pop("_g"); e["geom"] = rnd(simp(g), 4); out["extras"].append(e)
    import gzip
    (ROOT / "data" / "cshapes.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), 6))
    print("written", (ROOT / "data" / "cshapes.json.gz").stat().st_size)

if __name__ == "__main__":
    main()
