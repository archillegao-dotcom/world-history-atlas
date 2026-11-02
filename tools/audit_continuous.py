#!/usr/bin/env python3
"""连续日期审计：python tools/audit_continuous.py [起年 止年] [--monthly-from 1900]
1900 年起每月 1 日与 15 日、之前每年 7 月 1 日，对每个（过渡）快照的每个多边形解析政权（与地图标签/面板同一规则 R.primary），
检查政权存在期严格包含该日期（只有存在期本身只精确到年时，才允许同一年内的误差）。
旧审计（tools/audit.py）只取每年 7 月 1 日、且对年精度一律放宽一年，所以漏掉了月份级的问题。
结果：data/audit/continuous.json"""
from __future__ import annotations
import collections, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa
from backend.geo import BasemapStore  # noqa
from backend.polity import PolityResolver, lifespan  # noqa
from backend.timeutil import HDate, rec_key  # noqa

def alive(s, d):
    a, b, _ = lifespan(s)
    if a is None:
        return None
    ka = rec_key(a) if a.get("m") else rec_key({"y": a["y"], "m": 1, "d": 1, "p": 11})
    kb = None
    if b:
        kb = rec_key(b) if b.get("m") else rec_key({"y": b["y"], "m": 12, "d": 31, "p": 11})
    dk = d.key()
    return ka <= dk and (kb is None or dk <= kb)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    y0, y1 = (int(args[0]), int(args[1])) if len(args) == 2 else (-3000, 2026)
    B = BasemapStore(); R = PolityResolver(config.DATA_DIR); R.geo = B
    ds = []
    for y in range(y0, y1 + 1):
        if y == 0: continue
        if y >= 1900:
            ds += [HDate(y, m, dd) for m in range(1, 13) for dd in (1, 15)]
        else:
            ds.append(HDate(y, 7, 1))
    res = {"dates": 0, "polygons": 0, "violations": 0, "unknown": 0, "by_state": collections.Counter(), "examples": []}
    t0 = time.time()
    for d in ds:
        snap = B.snapshot_at(d); res["dates"] += 1
        for fid, f in B.features(snap).items():
            res["polygons"] += 1
            p = R.primary(R.resolve(snap, fid, d), d)
            if not p: continue
            if p.get("period"):
                # 整理过的分期（CShapes 分期 / 二战按月数据）：以分期为准；与 Wikidata 存在期不一致的另计，不算违规
                a8, b8 = p["period"]
                k8 = d.y * 10000 + (d.m or 7) * 100 + (d.d or 1)
                ok = (a8 is None or a8 <= k8) and (b8 is None or k8 < b8)
                if ok and alive(p["state"], d) is False:
                    res["period_vs_wikidata"] = res.get("period_vs_wikidata", 0) + 1
            else:
                ok = alive(p["state"], d)
            if ok is None: res["unknown"] += 1
            elif not ok:
                res["violations"] += 1
                k = f'{p["state"]["id"]} {p["state"].get("zh")}'
                res["by_state"][k] += 1
                if len(res["examples"]) < 200:
                    res["examples"].append([str(d.y) + "-" + str(d.m) + "-" + str(d.d), str(snap), fid, f["props"].get("NAME"), k, p["method"]])
    res["by_state"] = res["by_state"].most_common(60)
    res["seconds"] = round(time.time() - t0)
    out = config.DATA_DIR / "audit" / f"continuous_{y0}_{y1}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("dates", "polygons", "violations", "unknown", "seconds")}), res["by_state"][:25], sep="\n")
    for e in res["examples"][:40]: print(e)

if __name__ == "__main__":
    main()
