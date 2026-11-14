"""1937–1945 八个城市：占领层不得早于有证沦陷日。

读 data/control_zones.json.xz。早于沦陷日则失败。晚于沦陷日只打印，不失败。
另请接口确认 1937-12-10 南京点不是日军占领层。
用法：WHA_PORT=8792 python3 tools/accept/occupation_fall.py
"""
import json
import lzma
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[2]
# 沦陷日来自占领层原有说明和本批会战记载。检查的是「不早于」。
CITIES = [
    ("上海", 121.477, 31.233, "1937-11-12"),
    ("南京", 118.8, 32.06, "1937-12-13"),
    ("太原", 112.587, 37.839, "1937-11-08"),
    ("徐州", 117.257, 34.302, "1938-05-19"),
    ("武汉", 114.3, 30.59, "1938-10-25"),
    ("广州", 113.264, 23.122, "1938-10-21"),
    ("长沙", 112.971, 28.197, "1944-06-18"),
    ("桂林", 110.29, 25.27, "1944-11-10"),
    ("杭州", 120.169, 30.294, "1937-12-24"),
    ("苏州", 120.614, 31.318, "1937-11-19"),
    ("青岛", 120.038, 36.274, "1938-01-10"),
    ("厦门", 118.077, 24.460, "1938-05-13"),
    ("无锡", 120.291, 31.583, "1937-11-25"),
    ("常州", 119.943, 31.765, "1937-11-29"),
    ("芜湖", 118.370, 31.342, "1937-12-10"),
    ("济南", 116.998, 36.690, "1937-12-27"),
    ("开封", 114.345, 34.802, "1938-06-06"),
]
# 镇江：镇江县条目写12月8日县城失守，南京保卫战条目写12月6日天谷支队占领镇江。两天没有并成一天。
WATCH = [
    ("镇江", 119.455, 32.196, "12月6日和12月8日没有并成一天，不另挖"),
]

raw = lzma.decompress((ROOT / "data/control_zones.json.xz").read_bytes())
zones = []
for z in json.loads(raw)["zones"]:
    if z.get("kind") != "occupied" or not z.get("as_polity"):
        continue
    frm = z.get("from") or ""
    if frm < "1937-07-01" or frm >= "1946-01-01":
        continue
    zones.append((frm, z.get("until") or "", z["id"], shape(z["geom"])))

fails = []
for name, lon, lat, fall in CITIES:
    p = Point(lon, lat)
    hits = sorted(frm for frm, until, zid, g in zones if g.covers(p) or g.intersects(p))
    first = hits[0] if hits else None
    if first is None:
        print(f"FAIL {name} 没有占领层")
        fails.append(name)
        continue
    if first < fall:
        print(f"FAIL {name} 占领层 {first} 早于沦陷日 {fall}")
        fails.append(name)
    elif first > fall:
        print(f"NOTE {name} 占领层 {first} 晚于沦陷日 {fall}")
    else:
        print(f"PASS {name} 占领层 {first}")

for name, lon, lat, why in WATCH:
    p = Point(lon, lat)
    hits = sorted(frm for frm, until, zid, g in zones if g.covers(p) or g.intersects(p))
    first = hits[0] if hits else "没有占领层"
    print(f"NOTE {name} 占领层 {first}。{why}")

# 桂林县城点不在桂柳块里。上面用的是既有检查点。这里只记录，不失败。
seat = Point(110.164, 25.347)
if not any(g.covers(seat) for _, _, _, g in zones):
    print("NOTE 桂林县城点不在占领层里，检查用的是 25.27, 110.29")


def locate(date, lat, lon):
    q = urllib.parse.urlencode({"date": date, "lat": lat, "lon": lon})
    url = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}/api/locate?{q}"
    return json.load(urllib.request.urlopen(url, timeout=180))["polity"]


nj = locate("1937-12-10", 32.06, 118.8)
qid = str(nj.get("QID") or "")
name = nj.get("NAME_ZH") or nj.get("NAME") or ""
ok = qid != "Q188712" and "大日本" not in name and "日军" not in name
print(("PASS " if ok else "FAIL ") + f"1937-12-10 南京底图不是日军 | {qid} {name}")
if not ok:
    fails.append("nanjing-basemap")
nj14 = locate("1937-12-14", 32.06, 118.8)
qid14 = str(nj14.get("QID") or "")
name14 = nj14.get("NAME_ZH") or nj14.get("NAME") or ""
ok14 = qid14 == "Q188712" or "日军" in name14
print(("PASS " if ok14 else "FAIL ") + f"1937-12-14 南京底图是日军占领 | {qid14} {name14}")
if not ok14:
    fails.append("nanjing-14")
wh = locate("1938-10-24", 30.59, 114.3)
wh_name = wh.get("NAME_ZH") or wh.get("NAME") or ""
okwh = str(wh.get("QID") or "") != "Q188712" and "日军" not in wh_name
print(("PASS " if okwh else "FAIL ") + f"1938-10-24 武汉底图不是日军 | {wh.get('QID')} {wh_name}")
if not okwh:
    fails.append("wuhan-24")

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
