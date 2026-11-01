"""扫描某日期所有多边形对应的政权（leaders 模块），列出 state 及其起止年，找时代错乱。用法: scan_anachron.py -5000 -3000"""
import json, sys, gzip, urllib.request, urllib.parse
B = "http://127.0.0.1:8792"
def get(p, **kw): return json.load(urllib.request.urlopen(B + p + "?" + urllib.parse.urlencode(kw), timeout=180))
for date in sys.argv[1:]:
    s = get("/api/snapshot", date=date)["snapshot"]
    gj = json.loads(gzip.decompress(urllib.request.urlopen(B + "/api/basemap/" + urllib.parse.quote(str(s))).read()))
    print("==", date, s, len(gj["features"]))
    seen = {}
    for f in gj["features"]:
        pr = f["properties"]
        d = get("/api/modules/leaders", date=date, snap=s, fid=pr["fid"])
        st = d.get("state") or {}
        key = (pr.get("NAME"), st.get("id"))
        if key in seen: continue
        seen[key] = 1
        if st.get("id"):
            print(f"  {pr.get('NAME')!r:40} -> {st.get('id')} {st.get('name')} {st.get('start') or st.get('from')} {st.get('end') or st.get('to')} | heads={len(d.get('heads',[]))} offices={len(d.get('offices',[]))}")
    print("  (unmatched names omitted)")
