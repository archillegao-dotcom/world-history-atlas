"""扫描「快照之间政权更替」：某多边形在快照年份对应政权 A，到下一张快照之前 A 已解散、多边形被解析成别的政权 B
（如 1100 年快照的「Liao」在 1125 年后解析为金朝）。这些多边形的几何仍是 A 的范围，需要人工判断是否要补控制区几何。
输出 data/audit/succession_scan.json，按面积排序。"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import config
from backend.geo import BasemapStore
from backend.polity import PolityResolver
from backend.timeutil import HDate
sys.path.insert(0, str(ROOT / "tools"))
from audit import primary, inside

B = BasemapStore(); R = PolityResolver(config.DATA_DIR); R.geo = B
out = []
ys = [y for y in B.years if y > -3000]
for i, s in enumerate(ys[:-1]):
    n = ys[i + 1]
    d0 = HDate(s, 7, 1) if s > 0 else HDate(s, 0, 0)
    feats = B.features(s)
    p0 = {}
    for fid, f in feats.items():
        c = R.resolve(s, fid, d0); p = primary(c, d0)
        if p: p0[fid] = p["state"]
    seen = set()
    step = 1 if n - s <= 200 else 5
    for y in range(s + 1, n, step):
        if y == 0: continue
        d = HDate(y, 7, 1) if y > 0 else HDate(y, 0, 0)
        snap = B.snapshot_at(d)
        cf = B.features(snap) if snap != s else feats
        # 过渡层中仍是原快照几何的多边形（origin 指回基础快照的同一 fid）
        alive = {B.origin(snap, f2)[1]: f2 for f2 in cf if B.origin(snap, f2)[0] == s}
        for fid, st in p0.items():
            if fid in seen or inside(st, d.key()) or fid not in alive:
                continue
            seen.add(fid)
            c = R.resolve(snap, alive[fid], d); p = primary(c, d)
            f = feats[fid]
            out.append({"snap": s, "next": n, "NAME": f["props"].get("NAME"), "area": round(f["geom"].area, 1),
                        "was": [st["id"], st.get("zh") or st.get("en")], "dead_by": y,
                        "snap_at": str(snap), "now": p and [p["state"]["id"], p["state"].get("zh") or p["state"].get("en"), p["method"]]})
out.sort(key=lambda r: -r["area"])
(ROOT / "data/audit/succession_scan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out))
for r in out[:80]:
    print(r["snap"], "→", r["next"], r["NAME"], r["area"], r["was"][1], "解散于≈", r["dead_by"], "→", r["now"] and r["now"][1], r["now"] and r["now"][2])
