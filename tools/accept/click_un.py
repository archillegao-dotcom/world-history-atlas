"""
像用户一样点击：Playwright 打开前端，对每个联合国会员国（193 国，Wikidata P463=联合国 + 丹麦）在 Natural Earth 标注点处点击，
检查政权面板是否打开、标题是否有政权名；2020 年还核对解析出的 QID 是否为该国（或同一国家的条目）。
另对微型国家/小岛在世界尺度（z=2.5）点击最小尺寸圆点。
用法：.venv/bin/python tools/accept/click_un.py 2020-06-01 [zoom] [--micro] → logs/click_un_<date>.json，截图 screenshots/v08/click_<date>/
"""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[2]
B = "http://127.0.0.1:8792"
date = sys.argv[1]
zoom = float(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 5
micro = "--micro" in sys.argv
shard = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--shard=")), None)   # 例 --shard=0/3：并行分片
un = json.load(open(ROOT / "data/audit/un_members.json"))
un["Q35"] = "DNK"
# 同一国家的不同条目：荷兰王国（联合国会员，Q29999）在欧洲本土点到的是构成国「荷兰」Q55
SAME = {"Q29999": {"Q55"}}
ne = json.load(open(ROOT / "data/basemaps_raw/ne_10m_admin_0_countries.geojson"))
byq = {f["properties"].get("WIKIDATAID"): f["properties"] for f in ne["features"]}
byiso = {f["properties"].get("ADM0_A3"): f["properties"] for f in ne["features"]}
from shapely.geometry import shape, Point
geo = {f["properties"].get("ADM0_A3"): f["geometry"] for f in ne["features"]}
def inpt(p):
    """Natural Earth 标注点；落在海上（赤道几内亚、新西兰等）时改用多边形内点（representative_point）。"""
    g = shape(geo[p["ADM0_A3"]])
    if g.contains(Point(p["LABEL_X"], p["LABEL_Y"])):
        return p["LABEL_Y"], p["LABEL_X"]
    big = max(getattr(g, "geoms", [g]), key=lambda x: x.area)
    r = big.representative_point()
    return r.y, r.x
pts = []
for q, iso in sorted(un.items(), key=lambda x: x[1]):
    p = byq.get(q) or byiso.get(iso)
    pts.append((q, iso, p["NAME_ZH"] or p["ADMIN"], *inpt(p)))
MICRO = ["AND", "MCO", "SMR", "LIE", "VAT", "MLT", "SGP", "BHR", "MDV", "NRU", "TUV", "PLW", "MHL", "KIR", "KNA", "LCA", "VCT", "GRD", "ATG", "DMA", "BRB",
         "SYC", "COM", "MUS", "STP", "TON", "WSM", "FSM", "LUX", "HKG", "MAC", "CPV", "BRN", "TTO"]
if micro:
    pts = [(p.get("WIKIDATAID"), iso, p["NAME_ZH"] or p["ADMIN"], *inpt(p)) for iso in MICRO for p in [byiso[iso]]]
    zoom = 2.5
only = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--only=")), None)   # 例 --only=FRA,BHR：抽样
if only:
    pts = [p for p in pts if p[1] in only]
if shard:
    k, n_ = map(int, shard.split("/"))
    pts = [p for j, p in enumerate(pts) if j % n_ == k]
outdir = ROOT / "screenshots" / "v08" / f"click_{date}{'_micro' if micro else ''}"
outdir.mkdir(parents=True, exist_ok=True)
res = []
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto(f"{B}/#date={date}")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2500)
    for i, (q, iso, nm, lat, lon) in enumerate(pts):
        if i and i % 20 == 0:   # 长时间运行后页面变慢：每 20 国重新载入一次
            pg.goto("about:blank"); pg.goto(f"{B}/#date={date}"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2000)
        t = time.time()
        pg.evaluate(f"WHA.map.setView([{lat},{lon}], {zoom}, {{animate:false}})")
        pg.wait_for_timeout(400)
        pt = pg.evaluate(f"(() => {{ const q = WHA.map.latLngToContainerPoint([{lat},{lon}]); const r = document.getElementById('map').getBoundingClientRect(); return [q.x + r.left, q.y + r.top]; }})()")
        pg.evaluate("document.getElementById('polityName').textContent = ''")
        pg.mouse.click(*pt)
        name = None
        for _ in range(40):
            pg.wait_for_timeout(100)
            vis = pg.evaluate("!document.getElementById('panel').classList.contains('hidden')")
            name = pg.evaluate("document.getElementById('polityName').textContent").strip() if vis else None
            if name and name != "—":
                break
        st = pg.evaluate("WHA.state.fid")
        snap = pg.evaluate("WHA.state.snap")
        got = None
        if st is not None:
            try:
                got = pg.evaluate(f"WHA.api('/api/modules/regime?snap={snap}&fid={st}&date=' + WHA.dateParam()).then(r => [r.state && r.state.id].concat((r.merged || []).map(x => x.id)).concat(((r.chain || {{}}).now || []).map(x => x.qid)))")
                got = [x for x in got if x]
            except Exception as e:
                got = None
        ok = bool(name) and name != "—"
        exact = bool(got) and (q in got or bool(SAME.get(q, set()) & set(got)))
        r = {"qid": q, "iso": iso, "name": nm, "lat": lat, "lon": lon, "panel_name": name, "fid": st, "cands": (got or [])[:4], "panel": ok, "exact": exact,
             "sec": round(time.time() - t, 1)}
        res.append(r)
        print(("OK  " if ok else "MISS") + (" =" if exact else "  ") + f" {iso} {nm} → {name} {r['cands'][:2]}", flush=True)
        if not ok or (date >= "2020" and not exact) or i % 25 == 0:
            pg.screenshot(path=str(outdir / f"{i:03d}_{iso}{'' if ok else '_MISS'}.png"))
        pg.keyboard.press("Escape")
    br.close()
tag = date + ("_micro" if micro else "") + (f"_s{shard.split('/')[0]}" if shard else "") + ("_sample" if only else "")
json.dump({"date": date, "zoom": zoom, "results": res, "console_errors": errs[:20]}, open(ROOT / f"logs/click_un_{tag}.json", "w"), ensure_ascii=False, indent=1)
n = len(res); p = sum(r["panel"] for r in res); e = sum(r["exact"] for r in res)
print(f"PANEL {p}/{n} = {p / n:.1%}; EXACT-QID {e}/{n} = {e / n:.1%}; console errors {len(errs)}")
