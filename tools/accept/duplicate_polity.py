"""重复政权检查（v0.6.2）：同一快照里两个及以上的多边形默认解析到同一个政权 QID（真正的飞地/海外领土除外）。
离线运行（不需要服务）：.venv/bin/python tools/accept/duplicate_polity.py [YYYY-MM-DD ...]
默认日期：1816–2026 每 10 年的 1 月 1 日 + 1914–18、1938–45、1946–50 每半年。输出 logs/duplicate_polity.json。
判定「飞地」：两块多边形之间最近距离 > 3°（海外领地、远离本土的岛屿），或 ALLOW 中列出。"""
import json, sys
sys.path.insert(0, ".")
from types import SimpleNamespace
from backend.geo import BasemapStore
from backend import config
from backend.timeutil import HDate
from backend.modules import _state_common as SC

ALLOW = set()
B = BasemapStore(); ctx = SimpleNamespace(data_dir=config.DATA_DIR, shared={}, basemaps=B); R = SC.resolver(ctx)
if len(sys.argv) > 1:
    dates = [tuple(int(x) for x in a.split("-")) for a in sys.argv[1:]]
else:
    dates = [(y, 1, 1) for y in range(1816, 2027, 10)] + [(y, m, 1) for y in list(range(1914, 1919)) + list(range(1938, 1951)) for m in (1, 7)]
hits = []
for y, m, d in dates:
    date = HDate(y, m, d); snap = B.snapshot_at(date)
    by = {}
    for fid, f in B.features(snap).items():
        cands = R.resolve(snap, fid, date)
        p = R.primary(cands, date)
        if p:
            p = SC._prefer_ruled(ctx, R, cands, p, date, {"snap": snap})
            by.setdefault(p["state"]["id"], []).append((fid, f))
    for q, fs in by.items():
        if len(fs) < 2 or q in ALLOW:
            continue
        # v0.6.2 判定收紧：同一 QID 的相邻多边形只在「用户看得出是两个国家」时才算重复：
        #   前端着色键不同（app.js colorKey：SUBJECTO≠NAME 时用 SUBJECTO，否则用解析出的 QID），
        #   或两块面积都 ≥0.5 平方度且显示名称不同（如「苏联」与「Russia (Soviet Union)」）。
        #   同名的多块岛屿、微型国家碎片不算。
        def ck(f):
            pp = f["props"]; return pp.get("SUBJECTO") if pp.get("SUBJECTO") and pp.get("SUBJECTO") != pp.get("NAME") else q
        def nm(f):
            pp = f["props"]; return pp.get("NAME_ZH") or R.state_name(q)
        near = [(a[0], b[0]) for i, a in enumerate(fs) for b in fs[i + 1:]
                if a[1]["geom"].distance(b[1]["geom"]) < 3.0 and ((ck(a[1]) != ck(b[1]) and min(a[1]["geom"].area, b[1]["geom"].area) >= 0.05) or (
                    a[1]["geom"].area >= 0.5 and b[1]["geom"].area >= 0.5 and nm(a[1]) != nm(b[1])))]
        if near:
            hits.append({"date": f"{y}-{m:02d}-{d:02d}", "snap": str(snap), "qid": q, "name": R.state_name(q),
                         "features": [{"fid": fid, "name": f["props"].get("NAME_ZH") or f["props"].get("NAME"), "src": f["props"].get("SRC") or f["props"].get("TERR_CAT")} for fid, f in fs]})
            print(hits[-1]["date"], q, hits[-1]["name"], [x["name"] for x in hits[-1]["features"]], flush=True)
json.dump(hits, open("logs/duplicate_polity.json", "w"), ensure_ascii=False, indent=1)
print("HITS", len(hits), "dates", len(dates))
sys.exit(1 if hits else 0)
