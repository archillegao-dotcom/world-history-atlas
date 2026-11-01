"""调试：python tools/dev/q.py 日期,纬度,经度 ...  打印该点的政权与领导人"""
import json, sys, urllib.request, urllib.parse
B = "http://127.0.0.1:8792"
def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=180))
def show(date, lat, lon, mod="leaders", n=6):
    loc = get("/api/locate", date=date, lat=lat, lon=lon); p = loc["polity"]
    if not p: print(date, lat, lon, "no polygon"); return
    d = get(f"/api/modules/{mod}", date=date, snap=loc["snapshot"], fid=p["fid"])
    st = d.get("state") or {}
    print(f"== {date} ({lat},{lon}) [{loc['snapshot']}] {p['NAME']} -> {st.get('id')} {st.get('name')}")
    print("   alts:", [(a['id'], a['name'], a['method']) for a in d.get('alternatives', [])][:5])
    for h in d.get('heads', [])[:4]: print("   H", h['role'], h['person'].get('name'), h['from'], h['to'])
    for o in d.get('offices', [])[:n]: print("   O", o['office']['name'], [x['person'].get('name') for x in o['holders']])
if __name__ == "__main__":
    for a in sys.argv[1:]:
        d, la, lo = a.split(","); show(d, float(la), float(lo))
