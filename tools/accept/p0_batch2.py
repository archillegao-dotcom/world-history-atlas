"""第二批回归：满洲/热河、1949 两广、1945–49 台湾、2000 年法国、前 1136 周/商。
用法：WHA_PORT=8792 python3 tools/accept/p0_batch2.py
日期和政权来自公开页面，不是为了迎合某张旧表。"""
import json, os, sys, urllib.parse, urllib.request
B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"

def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=180))

def regime(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    if not p:
        return {"snap": loc.get("snapshot"), "poly": None}
    d = get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=p["fid"])
    st = d.get("state") or {}
    return {"snap": loc["snapshot"], "poly": p.get("NAME_ZH") or p.get("NAME"), "qid": st.get("id"),
            "name": st.get("name"), "from": st.get("from"), "flag": st.get("flag_file") or "",
            "chain": (d.get("chain") or {}).get("now") or [], "note": d.get("note") or ""}

fails = []
def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + got)
    if not cond:
        fails.append(label)

r = regime("1933-02-15", 40.97, 117.93)
check("1933-02-15承德还不是满洲国", r["qid"] != "Q30623", f"{r['qid']} {r['name']}")
r = regime("1933-04-15", 40.97, 117.93)
check("1933-04-15承德=满洲国", r["qid"] == "Q30623", f"{r['qid']} {r['name']}")
r = regime("1934-06-15", 44.0, 121.0)
check("1934兴安南=满洲国", r["qid"] == "Q30623" and "满" in (r["poly"] or "") + (r["name"] or ""), f"{r['poly']} {r['qid']}")
r = regime("1949-10-10", 23.13, 113.26)
check("1949-10-10广州=中华民国", r["qid"] in ("Q865", "Q13426199") and "人民" not in (r["name"] or ""), f"{r['poly']} {r['qid']} {r['name']}")
r = regime("1949-10-15", 23.13, 113.26)
check("1949-10-15广州=中华人民共和国", r["qid"] == "Q148", f"{r['poly']} {r['qid']} {r['name']}")
r = regime("1949-11-15", 25.27, 110.29)
check("1949-11-15桂林仍是广西中华民国控制区", "广西" in (r["poly"] or "") and r["qid"] in ("Q865", "Q13426199"), f"{r['poly']} {r['qid']}")
r = regime("1949-12-05", 22.82, 108.37)
check("1949-12-05南宁=中华人民共和国", r["qid"] == "Q148", f"{r['poly']} {r['qid']} {r['name']}")
r = regime("1945-10-20", 25.037, 121.564)
check("1945-10-20台北仍是日治", r["qid"] == "Q137816", f"{r['qid']} {r['name']}")
r = regime("1946-06-01", 25.037, 121.564)
check("1946台北=中华民国不是空的", r["qid"] in ("Q865", "Q13426199") and (r["poly"] or "") in ("Taiwan", "台湾"), f"{r['poly']} {r['qid']} {r['name']}")
r = regime("2000-06-01", 48.86, 2.35)
check("2000巴黎=第五共和国", r["qid"] == "Q142" and "第五共和国" in (r["name"] or ""), f"{r['qid']} {r['name']} from {r['from']}")
check("2000巴黎存在期不是481年起", (r["from"] or "").startswith("1958"), f"from {r['from']}")
check("2000巴黎是三色旗", "1976" in r["flag"] or "France.svg" in r["flag"], r["flag"][-80:])
r = regime("-1136-06-01", 33.665, 111.694)
check("前1136 Zhoa不是商朝", r["qid"] == "Q1069609" and not (r["name"] or "").startswith("商"), f"{r['qid']} {r['name']}")
check("前1136 Zhoa注明学术年代", "1046" in r["note"] and "传统" in r["note"], r["note"][:80])
r = regime("-1136-06-01", 33.665, 104.544)
check("前1136 Sinic仍是商", r["qid"] == "Q128938", f"{r['qid']} {r['name']}")
r = regime("1944-12-01", 25.27, 110.29)
check("1944-12桂林仍是日军", r["qid"] == "Q188712" and "汪" not in (r["poly"] or ""), f"{r['poly']} {r['qid']}")
print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
