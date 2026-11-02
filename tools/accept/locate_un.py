"""UN 193 国（与 click_un.py 同一点位：Natural Earth 标注点，落在海上时用多边形内点）经接口全量检查：
/api/locate 有多边形，且 /api/modules/regime 返回政权（id 或名称）。与地图点击走同一后端路径，但不经过浏览器渲染。
用法：.venv/bin/python tools/accept/locate_un.py 1950-06-01 → logs/locate_un_<date>.json"""
import json, sys
from pathlib import Path
from shapely.geometry import shape, Point
sys.path.insert(0, str(Path(__file__).parent))
import api_mustpass as A
ROOT = Path(__file__).resolve().parents[2]
date = sys.argv[1]
un = json.load(open(ROOT / "data/audit/un_members.json")); un["Q35"] = "DNK"
SAME = {"Q29999": {"Q55"}}
ne = json.load(open(ROOT / "data/basemaps_raw/ne_10m_admin_0_countries.geojson"))
byq = {f["properties"].get("WIKIDATAID"): f for f in ne["features"]}
byiso = {f["properties"].get("ADM0_A3"): f for f in ne["features"]}
res = []
for q, iso in sorted(un.items(), key=lambda x: x[1]):
    f = byq.get(q) or byiso.get(iso); p = f["properties"]; g = shape(f["geometry"])
    if g.contains(Point(p["LABEL_X"], p["LABEL_Y"])):
        lat, lon = p["LABEL_Y"], p["LABEL_X"]
    else:
        r = max(getattr(g, "geoms", [g]), key=lambda x: x.area).representative_point(); lat, lon = r.y, r.x
    loc = A.get("/api/locate", date=date, lat=lat, lon=lon); pol = loc.get("polity")
    st, ids = {}, []
    if pol:
        d = A.get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=pol["fid"])
        st = d.get("state") or {}
        ids = [x for x in [st.get("id")] + [(m.get("id") if isinstance(m, dict) else m) for m in d.get("merged") or []] + [(c.get("qid") if isinstance(c, dict) else c) for c in (d.get("chain") or {}).get("now") or []] if x]
    ok = bool(pol) and bool(st.get("id") or st.get("name"))
    exact = q in ids or bool(SAME.get(q, set()) & set(ids))
    res.append({"qid": q, "iso": iso, "lat": lat, "lon": lon, "snap": loc.get("snapshot"), "poly": (pol or {}).get("NAME_ZH") or (pol or {}).get("NAME"),
                "state": st.get("id"), "name": st.get("name"), "ok": ok, "exact": exact})
    print(("OK  " if ok else "MISS") + (" =" if exact else "  ") + f" {iso} → {st.get('name')} {st.get('id')}", flush=True)
json.dump({"date": date, "results": res}, open(ROOT / f"logs/locate_un_{date}.json", "w"), ensure_ascii=False, indent=1)
n = len(res); o = sum(r["ok"] for r in res); e = sum(r["exact"] for r in res)
print(f"LOCATE+REGIME {o}/{n} = {o / n:.1%}; 即当今国家 QID {e}/{n}")
