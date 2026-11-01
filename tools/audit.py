#!/usr/bin/env python3
"""
数据一致性审计（自动）：python tools/audit.py [--baseline 旧版代码目录] [--quick]

检查项（结果写入 data/audit/audit_results.json，AUDIT_REPORT.md 引用其中的数字）：
 1. 地图多边形 ↔ 政权存在期：公元前每 50 年、公元后每年（7 月 1 日）对每张（过渡）快照的每个多边形解析政权，
    主要政权与全部「强」候选的存在期（Wikidata P571/P576，缺失时用最早/最晚的带时间语句）必须包含该日期；
    同时统计「没有任何政权、只显示底图名称（文化/地区）」的多边形数。
    --baseline 给出 v0.4.0 代码目录时，用旧版解析规则在同一批日期上统计违规数（「修复前」）。
 2. 领导人面板：抽样日期 × 全部多边形，面板中每个职位的管辖政权必须与主要政权同名（不混入另一个政权），
    任职时间必须覆盖所选日期；旧版合并规则下混入其他政权职位的次数作为「修复前」。
 3. 政体/意识形态：带时间的政体语句是否落在政权存在期内；起止颠倒。
 4. 阵营：成员加入/退出时间是否落在阵营存在期与成员存在期内；起止颠倒。
 5. 条约：生效/终止颠倒；签署方在签订日期是否存在。
 6. 城市：作为首都的时间段起止颠倒；城市「首都」记录指向的政权存在期。
 7. 事件：日期超出 -123000…今天；结束早于开始；国家标签（P17）是现代国家而事件早于其成立（不影响按坐标归属）。
 8. 经济：台湾/中国、前苏联等的 Maddison/WDI 国家代码映射。
"""
from __future__ import annotations

import collections
import datetime
import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config  # noqa: E402
from backend.datafile import read_json  # noqa: E402
from backend.geo import BasemapStore  # noqa: E402
from backend.polity import PolityResolver, lifespan  # noqa: E402
from backend.timeutil import HDate, rec_key  # noqa: E402

OUT = config.DATA_DIR / "audit"
TODAY = datetime.date.today()


def inside(s, dk, slack_year=True):
    a, b, _ = lifespan(s)
    if a is None:
        return False
    sa = 1.0 if slack_year and not a.get("m") else 0.0
    sb = 1.0 if (b and slack_year and not b.get("m")) else 0.0
    return rec_key(a) - sa <= dk and (b is None or dk <= rec_key(b) + sb)


def dates(quick=False):
    bce = list(range(-123000, 0, 50 if not quick else 500))
    ce = list(range(1, TODAY.year + 1, 1 if not quick else 10))
    return [HDate(y, 7 if y > 0 else 0, 1 if y > 0 else 0) for y in bce + ce]


def primary(cands, date):
    return PolityResolver.primary(cands, date)


def check_lifespans(B, R, Rold, quick):
    res = {"dates": 0, "polygons": 0, "violations": 0, "strong_violations": 0, "unmatched": 0, "examples": [],
           "before": {"violations": 0, "unknown_lifespan": 0, "examples": []}}
    t0 = time.time()
    for d in dates(quick):
        snap = B.snapshot_at(d)
        res["dates"] += 1
        dk = d.key()
        base = B.base_of(snap)
        for fid, f in B.features(snap).items():
            res["polygons"] += 1
            cands = R.resolve(snap, fid, d)
            p = primary(cands, d)
            if p is None:
                res["unmatched"] += 1
            elif not inside(p["state"], dk):
                res["violations"] += 1
                if len(res["examples"]) < 30:
                    res["examples"].append([d.y, f["props"].get("NAME"), p["state"]["id"], p["state"].get("zh")])
            for c in cands:
                if c["strong"] and not inside(c["state"], dk):
                    res["strong_violations"] += 1
            if Rold is not None and fid < 100000:
                oc = Rold.resolve(base, fid, d)
                if oc:
                    s = oc[0]["state"]
                    if s.get("from") is None:
                        res["before"]["unknown_lifespan"] += 1
                    if not inside(s, dk):
                        res["before"]["violations"] += 1
                        if len(res["before"]["examples"]) < 30 and (d.y < 0 or d.y % 25 == 0):
                            res["before"]["examples"].append([d.y, f["props"].get("NAME"), s["id"], s.get("zh")])
    res["seconds"] = round(time.time() - t0)
    return res


def check_leaders(B, R, quick):
    """领导人面板：用与 leaders 模块相同的合并规则，检查混入其他政权的职位与任期。"""
    from backend.modules import leaders as L
    from backend.modules._state_common import pick_state

    class Ctx:
        shared = {"polity": R}
        basemaps = B
        data_dir = config.DATA_DIR
    ys = list(range(1500, 1900, 25)) + list(range(1900, TODAY.year + 1, 5 if not quick else 20))
    res = {"panels": 0, "offices": 0, "cross_state": 0, "examples": [],
           "before_cross_state": 0, "before_examples": []}
    for y in ys:
        d = HDate(y, 7, 1)
        snap = B.snapshot_at(d)
        dk = d.key()
        for fid, f in B.features(snap).items():
            params = {"snap": snap}
            st, _ = pick_state(Ctx, f, d, params)
            if not st:
                continue
            res["panels"] += 1
            out = L.MODULE.query(Ctx, f, d, {"snap": snap})
            pz = st.get("zh") or st.get("en")
            cands = R.resolve(snap, fid, d)
            by_id = {c["state"]["id"]: c for c in cands}
            # 不变量：面板合并的其他条目 (1) 首都不在另一个多边形里（未被「另有所在」降级）；
            # (2) 与主要政权没有「被取代/取代」关系（如 中华民国(1912–1949) ↔ 中华人民共和国）。违反即视为混入其他政权
            rivals = set()
            for m in params.get("_strong", []):
                if m["id"] == st["id"]:
                    continue
                c = by_id.get(m["id"], {})
                def later(a, b):   # b 的成立时间晚于 a：真正的「继承」关系（排除 Wikidata 中「法兰西王国 → 法国(481 年起)」这类粒度关系）
                    ka, kb = rec_key(a.get("from")), rec_key(b.get("from"))
                    return ka is None or kb is None or kb > ka
                rel = (any(x["v"] == st["id"] for x in m.get("replaced_by", [])) and later(m, st)) or \
                      (any(x["v"] == m["id"] for x in st.get("replaced_by", [])) and later(st, m))
                if c.get("elsewhere") is not None or (rel and (m.get("zh") or m.get("en")) != pz):
                    rivals.add(m.get("zh") or m.get("en"))
            for o in out.get("offices", []):
                res["offices"] += 1
                if o.get("src") and o["src"] in rivals:
                    res["cross_state"] += 1
                    if len(res["examples"]) < 20:
                        res["examples"].append([y, f["props"].get("NAME"), st.get("zh"), o["src"], o["office"]["name"]])
            res.setdefault("merged_panels", 0)
            if len(params.get("_strong", [])) > 1:
                res["merged_panels"] += 1
                if len(res.setdefault("merged_examples", [])) < 25 and y % 50 == 0:
                    res["merged_examples"].append([y, f["props"].get("NAME"), [m.get("zh") for m in params["_strong"]]])
            # 旧版规则：同一区域全部强候选的职位都合并显示
            for c in cands:
                if c["state"]["id"] == st["id"] or not (c["strong"] or c.get("elsewhere") is not None):
                    continue
                if (c["state"].get("zh") or c["state"].get("en")) == pz:
                    continue
                n = sum(1 for o in R.office_by_state.get(c["state"]["id"], [])
                        if L._holding(o.get("holders", []), dk))
                if n:
                    res["before_cross_state"] += n
                    if len(res["before_examples"]) < 20:
                        res["before_examples"].append([y, f["props"].get("NAME"), st.get("zh"), c["state"].get("zh"), n])
    return res


def check_leader_terms(B, R, quick):
    """领导人面板中显示的每一位任职者：任期必须覆盖所选日期（开始 ≤ 日期 ≤ 结束；无结束日期时按 leaders._holding 规则），
    职位管辖政权必须是面板政权或其合并条目。抽样：1500–1900 每 25 年、1900 至今每 5 年，全部多边形。"""
    from backend.modules import leaders as L
    from backend.modules._state_common import pick_state

    class Ctx:
        shared = {"polity": R}
        basemaps = B
        data_dir = config.DATA_DIR
    ys = list(range(1500, 1900, 25)) + list(range(1900, TODAY.year + 1, 5 if not quick else 20))
    res = {"panels": 0, "holders": 0, "term_violations": 0, "juris_violations": 0, "non_leadership_shown": 0, "examples": []}
    by_id = {o["id"]: o for o in R.offices}
    for y in ys:
        d = HDate(y, 7, 1)
        snap = B.snapshot_at(d)
        dk = d.key()
        for fid, f in B.features(snap).items():
            params = {"snap": snap}
            st, _ = pick_state(Ctx, f, d, params)
            if not st:
                continue
            res["panels"] += 1
            out = L.MODULE.query(Ctx, f, d, {"snap": snap})
            group = {st["id"]} | {m["id"] for m in params.get("_strong", [])}
            for o in out.get("offices", []):
                src = by_id.get(o["office"]["id"], {})
                if L.is_envoy(src):
                    res["non_leadership_shown"] += 1
                if not set(src.get("juris", [])) & group:
                    res["juris_violations"] += 1
                    if len(res["examples"]) < 20:
                        res["examples"].append(["juris", y, f["props"].get("NAME"), st.get("zh"), o["office"]["name"]])
                shown = {x["person"]["id"] for x in o["holders"]}

                def covers(h):
                    if not h.get("from"):
                        return False
                    # 年精度给 1 年余量，月精度（d=0）给 1 个月余量（rec_key 把未知日放在月中）
                    a = rec_key(h["from"]) - (1.0 if not h["from"].get("m") else (1 / 12 if not h["from"].get("d") else 0))
                    if a > dk:
                        return False
                    if not h.get("to"):
                        return True          # 无卸任日期：按 leaders._holding 的规则（15 年内、之后无人接任）显示
                    return dk <= rec_key(h["to"]) + (1.0 if not h["to"].get("m") else (1 / 12 if not h["to"].get("d") else 0))
                for pid in shown:
                    terms = [h for h in src.get("holders", []) if h["p"] == pid]
                    if not terms:
                        continue
                    res["holders"] += 1
                    if not any(covers(h) for h in terms):
                        res["term_violations"] += 1
                        if len(res["examples"]) < 20:
                            res["examples"].append(["term", y, st.get("zh"), o["office"]["name"], pid,
                                                    [(h.get("from"), h.get("to")) for h in terms][:3]])
    return res


def check_city_country(B, R):
    """城市归属：有明确起止限定（P1376 + P580/P582）的首都记录，在其任期中点，城市坐标所在多边形的政权候选中应包含该国家。"""
    cs = read_json(config.DATA_DIR / "cities.json.gz", [])
    res = {"dated_capital_records": 0, "checked": 0, "match": 0, "mismatch": 0, "no_polygon": 0, "examples": []}
    for c in cs:
        for k in c.get("capital", []):
            if not (k.get("from") and k.get("to")):
                continue
            res["dated_capital_records"] += 1
            a, b = rec_key(k["from"]), rec_key(k["to"])
            mid = (a + b) / 2
            if mid < 1 or b < a:
                continue
            y = int(mid)
            d = HDate(y, 7, 1)
            snap = B.snapshot_at(d)
            f = B.locate(snap, c["coord"][0], c["coord"][1])
            if not f:
                res["no_polygon"] += 1
                continue
            res["checked"] += 1
            cands = R.resolve(snap, f["props"]["fid"], d)
            ids = {x["state"]["id"] for x in cands}
            if k["of"] in ids:
                res["match"] += 1
            else:
                res["mismatch"] += 1
                if len(res["examples"]) < 25:
                    p = primary(cands, d)
                    res["examples"].append([c.get("zh") or c.get("en"), y, (R.states.get(k["of"]) or {}).get("zh") or k["of"],
                                            f["props"].get("NAME"), p and p["state"].get("zh")])
    return res


def check_event_attribution(B, R, limit=20000):
    """事件归属：1500 年以后、有坐标与国家标签（P17）的事件，按坐标落入的多边形解析政权；
    统计「事件的国家标签（当时存在的）之一就是该政权」的比例。不一致多为 P17 记的是现代国家，按坐标归属不受影响。"""
    ev = read_json(config.DATA_DIR / "events.json.gz", [])
    res = {"checked": 0, "match": 0, "mismatch": 0, "no_polity": 0, "tag_not_alive": 0, "examples": []}
    n = 0
    for e in ev:
        st = e.get("start")
        if not st or st["y"] < 1500 or not e.get("coord") or not e.get("countries"):
            continue
        n += 1
        if n > limit:
            break
        d = HDate(st["y"], 7, 1)    # 按年中检查（与存在期检查共用同一批过渡快照，避免为每个具体日期重建几何）
        dk = d.key()
        alive_tags = [q for q in e["countries"] if R.states.get(q) and inside(R.states[q], dk)]
        if not alive_tags:
            res["tag_not_alive"] += 1
            continue
        snap = B.snapshot_at(d)
        f = B.locate(snap, e["coord"][0], e["coord"][1])
        if not f:
            res["no_polity"] += 1
            continue
        cands = R.resolve(snap, f["props"]["fid"], d)
        if not cands:
            res["no_polity"] += 1
            continue
        res["checked"] += 1
        if set(alive_tags) & {x["state"]["id"] for x in cands}:
            res["match"] += 1
        else:
            res["mismatch"] += 1
            if len(res["examples"]) < 20:
                p = primary(cands, d)
                res["examples"].append([e.get("name"), st["y"], [R.states[q].get("zh") for q in alive_tags], f["props"].get("NAME"), p and p["state"].get("zh")])
    return res


def check_control_zones(B, R):
    """实际控制区：日期可解析、起止不颠倒、控制方在区间内存在、几何非空。"""
    from backend import control_zones as CZ
    from shapely.geometry import shape
    zs = CZ.load(config.DATA_DIR)
    res = {"zones": len(zs), "approx": sum(1 for z in zs if z.get("approx")), "as_polity": sum(1 for z in zs if z.get("as_polity")),
           "reversed": 0, "controller_not_alive": 0, "empty_geom": 0, "no_source": 0, "examples": []}
    for z in zs:
        a, b = CZ.parse(z.get("from")), CZ.parse(z.get("until"), end=True)
        if a and b and rec_key(b) <= rec_key(a):
            res["reversed"] += 1
        s = R.states.get(z["controller"]["qid"])
        if s and a and not inside(s, rec_key(a)):
            res["controller_not_alive"] += 1
            res["examples"].append([z["id"], "controller", z["controller"]])
        if shape(z["geom"]).is_empty:
            res["empty_geom"] += 1
        if not z.get("sources"):
            res["no_source"] += 1
    return res


def check_regime(R):
    bad_order, outside, total = 0, 0, 0
    ex = []
    for s in R.states.values():
        for g in s.get("gov", []) + s.get("ideology", []):
            if not (g.get("from") or g.get("to")):
                continue
            total += 1
            a, b = rec_key(g.get("from")), rec_key(g.get("to"))
            if a is not None and b is not None and b < a:
                bad_order += 1
            la, lb, _ = lifespan(s)
            if (a is not None and lb is not None and a > rec_key(lb) + 1) or (b is not None and la is not None and b < rec_key(la) - 1):
                outside += 1
                if len(ex) < 15:
                    ex.append([s["id"], s.get("zh"), g.get("zh") or g.get("en"), g.get("from"), g.get("to")])
    return {"dated_labels": total, "reversed": bad_order, "outside_lifespan": outside, "examples": ex}


def check_alliances(R):
    al = read_json(config.DATA_DIR / "alliances.json.gz", [])
    res = {"alliances": len(al), "members": 0, "reversed": 0, "outside_alliance": 0, "member_not_alive": 0, "examples": []}
    for a in al:
        A0, A1 = rec_key(a.get("from")), rec_key(a.get("to"))
        if A0 is not None and A1 is not None and A1 < A0:
            res["reversed"] += 1
        for m in a.get("members", []):
            res["members"] += 1
            f, t = rec_key(m.get("from")), rec_key(m.get("to"))
            if f is not None and t is not None and t < f:
                res["reversed"] += 1
            if f is not None and ((A0 is not None and f < A0 - 1) or (A1 is not None and f > A1 + 1)):
                res["outside_alliance"] += 1
                if len(res["examples"]) < 10:
                    res["examples"].append([a.get("zh") or a.get("en"), m["s"], m.get("from")])
            s = R.states.get(m["s"])
            k = f if f is not None else A0
            if s and k is not None and not inside(s, k):
                res["member_not_alive"] += 1
    return res


def check_treaties(R):
    tr = read_json(config.DATA_DIR / "treaties.json.gz", [])
    res = {"treaties": len(tr), "reversed": 0, "party_not_alive": 0, "parties": 0, "examples": []}
    from backend.modules.spirits import tend, tstart
    for t in tr:
        a, b = tstart(t), tend(t)
        if a and b and rec_key(b) < rec_key(a):
            res["reversed"] += 1
        for p in t.get("parties", []):
            q = p.get("s") if isinstance(p, dict) else p
            s = R.states.get(q)
            if not s or not a:
                continue
            res["parties"] += 1
            if not inside(s, rec_key(a)):
                res["party_not_alive"] += 1
                if len(res["examples"]) < 10:
                    res["examples"].append([t.get("zh") or t.get("en"), q, s.get("zh"), a])
    return res


def check_cities(R):
    global FIXES
    import json as _j
    FIXES = _j.loads((config.DATA_DIR / "curated" / "capital_fixes.json").read_text(encoding="utf-8"))
    cs = read_json(config.DATA_DIR / "cities.json.gz", [])
    res = {"cities": len(cs), "capital_records": 0, "reversed": 0, "future_from": 0}
    for c in cs:
        if c.get("from") and c["from"]["y"] > TODAY.year:
            res["future_from"] += 1
        for k in c.get("capital", []):
            res["capital_records"] += 1
            a, b = rec_key(k.get("from")), rec_key(k.get("to"))
            if a is not None and b is not None and b < a:
                res["reversed"] += 1
            if a is None and b is not None:
                res["to_only"] = res.get("to_only", 0) + 1     # 图层中开始时间取政权成立时间
            # 无起止限定、按政权整个存在期（>300 年）当作首都：可能把迁都前后的年代也标成首都
            if a is None and b is None:
                sa, sb = rec_key(k.get("state_from")), rec_key(k.get("state_to"))
                if sa is not None and (sb if sb is not None else TODAY.year) - sa > 300:
                    fixed = k.get("of") in FIXES.get(c["id"], {})
                    res["undated_long_capital_fixed" if fixed else "undated_long_capital"] = \
                        res.get("undated_long_capital_fixed" if fixed else "undated_long_capital", 0) + 1
                    if not fixed and len(res.setdefault("examples", [])) < 40:
                        res["examples"].append([c.get("zh") or c.get("en"), k.get("of"), k.get("state_from"), k.get("state_to")])
    return res


def check_events(R):
    ev = read_json(config.DATA_DIR / "events.json.gz", [])
    res = {"events": len(ev), "out_of_range": 0, "reversed": 0, "anachronistic_country_tag": 0, "examples": []}
    for e in ev:
        a, b = rec_key(e.get("start")), rec_key(e.get("end"))
        if a is not None and (a < -123000 or a > TODAY.year + 1):
            res["out_of_range"] += 1
        if a is not None and b is not None and b < a:
            res["reversed"] += 1
        for q in e.get("countries", []):
            s = R.states.get(q)
            if s and a is not None and s.get("from") and rec_key(s["from"]) > a + 1:
                res["anachronistic_country_tag"] += 1
                if len(res["examples"]) < 10:
                    res["examples"].append([e.get("name"), e["start"]["y"], s.get("zh")])
                break
    return res


def check_econ(B):
    from backend.econ import EconStore
    S = EconStore(config.DATA_DIR)
    res = {"unmapped_named": {}}
    for snap_date in ("1950-07-01", "1975-07-01", "1995-07-01", "2020-07-01"):
        y, m, d = map(int, snap_date.split("-"))
        snap = B.snapshot_at(HDate(y, m, d))
        ov = S.overlap_for(B, snap)
        fs = B.features(snap)
        named = [f for f in fs.values() if f["props"].get("NAME")]
        un = [f["props"]["NAME"] for f in named if not ov.get(str(f["props"]["fid"]))]
        res["unmapped_named"][snap_date] = {"named": len(named), "unmapped": len(un), "examples": un[:15]}
    for snap_date in ("1950-07-01", "1975-07-01", "2020-07-01"):
        y, m, d = map(int, snap_date.split("-"))
        dt = HDate(y, m, d)
        snap = B.snapshot_at(dt)
        ov = S.overlap_for(B, snap)
        row = {}
        for nm in ("China", "Taiwan", "USSR", "Hong Kong S.A.R.", "Hong Kong"):
            for fid, f in B.features(snap).items():
                if f["props"].get("NAME") == nm:
                    row[nm] = ov.get(str(fid))
        res[snap_date] = row
    res["has_TWN_maddison"] = "TWN" in S.mpd
    res["has_HKG_maddison"] = "HKG" in S.mpd
    return res


def treaty_coverage():
    import re as _re
    cjk = _re.compile(r"[\u4e00-\u9fff]")
    t = read_json(config.DATA_DIR / "treaties.json.gz", [])
    n = len(t) or 1

    def pct(c):
        return {"n": c, "pct": round(100 * c / n, 1)}
    return {"treaties": len(t),
            "zh_name_native": pct(sum(1 for x in t if cjk.search(x.get("zh") or "") and not x.get("zh_mt"))),
            "zh_name_any": pct(sum(1 for x in t if cjk.search(x.get("zh") or ""))),
            "zh_summary_native": pct(sum(1 for x in t if (x.get("summary") or {}).get("src") == "zh.wikipedia")),
            "zh_summary_any": pct(sum(1 for x in t if cjk.search((x.get("summary") or {}).get("text") or ""))),
            "parties": pct(sum(1 for x in t if x.get("parties"))),
            "signed_date": pct(sum(1 for x in t if x.get("signed") or x.get("start") or x.get("inception"))),
            "effective": pct(sum(1 for x in t if x.get("effective"))),
            "end": pct(sum(1 for x in t if x.get("end") or x.get("dissolved"))),
            "location": pct(sum(1 for x in t if x.get("location"))),
            "link": pct(sum(1 for x in t if x.get("zhwiki") or x.get("enwiki")))}


def china_table(B, R):
    pts = {"洛阳": (112.45, 34.62), "杭州": (120.15, 30.27), "北京": (116.4, 39.9)}
    ys = list(range(-2000, 1951, 100)) + list(range(180, 281, 10)) + list(range(900, 1281, 10))
    rows = []
    for y in sorted(set(ys)):
        if y == 0:
            continue
        d = HDate(y, 7, 1)
        snap = B.snapshot_at(d)
        row = {"year": y, "snap": str(snap)}
        for k, (lon, lat) in pts.items():
            f = B.locate(snap, lon, lat)
            if not f:
                row[k] = ["-", None, []]
                continue
            cands = R.resolve(snap, f["props"]["fid"], d)
            p = primary(cands, d)
            row[k] = [f["props"].get("NAME"), p and (p["state"].get("zh") or p["state"].get("en")),
                      [c["state"].get("zh") for c in cands if c["strong"] and c is not p][:4]]
        rows.append(row)
    return rows


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    B = BasemapStore()
    R = PolityResolver(config.DATA_DIR)
    R.geo = B
    Rold = None
    if "--baseline" in sys.argv:
        bdir = Path(sys.argv[sys.argv.index("--baseline") + 1])
        sys.path.insert(0, str(bdir))
        # 旧版 polity.py 使用相对导入：在包上下文中加载
        import types
        pkg = types.ModuleType("oldbackend")
        pkg.__path__ = [str(bdir / "backend")]
        sys.modules["oldbackend"] = pkg
        old = importlib.import_module("oldbackend.polity")
        Rold = old.PolityResolver(config.DATA_DIR)
    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds")}
    for name, fn in (("lifespan", lambda: check_lifespans(B, R, Rold, quick)), ("leaders", lambda: check_leaders(B, R, quick)),
                     ("leader_terms", lambda: check_leader_terms(B, R, quick)), ("city_country", lambda: check_city_country(B, R)),
                     ("event_attribution", lambda: check_event_attribution(B, R)), ("control_zones", lambda: check_control_zones(B, R)),
                     ("regime", lambda: check_regime(R)), ("alliances", lambda: check_alliances(R)),
                     ("treaties", lambda: check_treaties(R)), ("cities", lambda: check_cities(R)),
                     ("events", lambda: check_events(R)), ("econ", lambda: check_econ(B)), ("china", lambda: china_table(B, R)),
                     ("treaty_coverage", treaty_coverage), ("official_offices", lambda: R.official_stats)):
        t0 = time.time()
        out[name] = fn()
        print(f"[{name}] {time.time() - t0:.0f}s", {k: v for k, v in out[name].items() if not isinstance(v, (list, dict))}
              if isinstance(out[name], dict) else len(out[name]), flush=True)
        (OUT / "audit_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
