"""回归测试：1939-09 至 1945-08 每月，所有带占领方的区域（Stanford WW2_STATUS 含 occupied/annexed/administered，
或控制区 TERR_CAT=zone_occupied）在阵营图层里必须属于轴心国(Q43056)或同盟国(Q329888)之一，
或带 client_of（附庸/保护国，不计入签署国）。
用法：WHA_PORT=8792 python tools/accept/ww2_occupation_bloc.py"""
import json, os, sys, urllib.request, collections, gzip
PORT = os.environ.get("WHA_PORT", "8792")
def get(u):
    b = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{u}").read()
    return json.loads(gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b)
miss = collections.defaultdict(list); n = 0; seen = set()
for y in range(1939, 1946):
    for m in range(1, 13):
        if (y, m) < (1939, 9) or (y, m) > (1945, 8): continue
        d = f"{y}-{m:02d}-15"
        al = get(f"/api/layers/alliances?date={d}")
        if al["snapshot"] in seen: continue
        seen.add(al["snapshot"])
        mem = set()
        for a in al["alliances"]:
            if a["id"] in ("Q43056", "Q329888"): mem |= set(a["members"])
        bm = get(f"/api/basemap/{al['snapshot']}")
        for f in bm["features"]:
            p = f["properties"]; st = (p.get("WW2_STATUS") or "").lower()
            occ = any(k in st for k in ("occupied", "annexed", "administ")) or p.get("TERR_CAT") == "zone_occupied"
            if not occ: continue
            n += 1
            states = set(al["polity_states"].get(str(p["fid"]), []))
            client = (al.get("client_of") or {}).get(str(p["fid"])) or {}
            if not (mem & states) and client.get("bloc") not in ("Q43056", "Q329888"):
                miss[(p.get("NAME_ZH") or p.get("NAME"), p.get("WW2_STATUS") or p.get("TERRITORY"))].append(d)
print(f"snapshots={len(seen)} occupied-zone-checks={n} zones-without-bloc={len(miss)}")
for k, v in sorted(miss.items(), key=lambda kv: -len(kv[1])):
    print("  MISS", k, len(v), v[0], "…", v[-1])
sys.exit(1 if miss else 0)
