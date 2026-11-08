"""第五批：1944-12-01 满洲国西缘那块褐色缺口改到蒙疆，两侧仍是满洲国和外蒙古。
用法：WHA_PORT=8792 python3 tools/accept/p0_batch5.py
"""
import json, os, sys, urllib.parse, urllib.request
B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"

def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=180))

def poly(date, lat, lon):
    p = (get("/api/locate", date=date, lat=lat, lon=lon).get("polity") or {})
    return (p.get("NAME_ZH") or "") + "|" + (p.get("NAME") or "")

fails = []
def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:160])
    if not cond:
        fails.append(label)

D = "1944-12-01"
# 缺口内部：原 CShapes「China」露出色，现为蒙疆近似范围
for lat, lon, nm in [(45.40, 118.75, "缺口中"), (45.20, 118.35, "缺口西"), (46.20, 118.30, "缺口北")]:
    g = poly(D, lat, lon)
    check(f"{nm}是蒙疆", "蒙疆" in g, g)
# 东侧仍是满洲国，北侧仍是外蒙古，腹地和河套、西安没有被吞掉
for lat, lon, nm, needle in [
    (45.40, 120.40, "满洲国西缘以东", "满洲"),
    (44.00, 121.00, "兴安南", "满洲"),
    (49.20, 119.75, "海拉尔", "满洲"),
    (42.27, 118.95, "赤峰", "满洲"),
    (40.97, 117.93, "承德", "满洲"),
    (43.20, 113.70, "蒙疆腹地", "蒙疆"),
    (46.80, 117.50, "外蒙古", "Mongolia"),
    (46.60, 117.90, "外蒙古南缘", "Mongolia"),
    (34.26, 108.94, "西安", "China"),
    (40.80, 107.40, "河套", "China"),
]:
    g = poly(D, lat, lon)
    check(nm, needle in g and ("蒙疆" not in g or needle == "蒙疆"), g)

print(f"fails={len(fails)}")
sys.exit(1 if fails else 0)
