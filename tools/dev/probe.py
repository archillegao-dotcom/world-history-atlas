"""探针：python tools/dev/probe.py DATE LAT LON → 该点政权 QID、元首、职位、摄政。"""
import json, sys, urllib.parse, urllib.request
B = "http://127.0.0.1:8792"
def get(p, **kw):
    return json.load(urllib.request.urlopen(B + p + "?" + urllib.parse.urlencode(kw), timeout=300))
d, la, lo = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
loc = get("/api/locate", date=d, lat=la, lon=lo); p = loc.get("polity")
if not p: print("无多边形"); sys.exit()
L = get("/api/modules/leaders", date=d, snap=loc["snapshot"], fid=p["fid"])
st = L.get("state") or {}
print(d, p.get("NAME"), "→", st.get("id"), st.get("name"), "| merged", [m["id"] for m in L.get("merged", [])])
for h in L.get("heads", []): print("  H", h["role"], h["person"].get("name"), h.get("from"), h.get("to"), h.get("kind") or "")
for o in L.get("offices", [])[:6]: print("  O", o["office"]["name"], [x["person"].get("name") for x in o["holders"]])
for r in L.get("regents", []): print("  R", r["person"].get("name"), r["role"])
for c in L.get("interregna", []):
    print("  I", c["kind"], c["title"], [(x["tag"], x["person"]["name"]) for x in c["leaders"]], "alt" if c.get("alt") else "")
