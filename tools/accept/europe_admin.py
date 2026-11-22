"""欧洲历史一级行政区。有几何的点必须对上当年的建制，没有几何的点仍是省界待考。

用法：WHA_PORT=8792 python3 tools/accept/europe_admin.py
"""
import json, os, sys, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    q = "?" + urllib.parse.urlencode(kw) if kw else ""
    return json.load(urllib.request.urlopen(B + path + q, timeout=180))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:220])
    if not cond:
        fails.append(label)


def place(date, lat, lon):
    return get("/api/modules/roc_admin", date=date, lat=lat, lon=lon)["place"]


def layer(date):
    return get("/api/layers/europe_admin", date=date)


cases = [
    ("1910-06-01", 48.2082, 16.3738, "下奥地利", "王冠领地", "CC BY 4.0"),
    ("1910-06-01", 50.087, 14.421, "波希米亚", "王冠领地", "CC BY 4.0"),
    ("1914-06-01", 54.71, 20.51, "东普鲁士", "省", "CC BY 4.0"),
    ("1850-06-01", 48.137, 11.575, "巴伐利亚", "王国", "CC BY 4.0"),
    ("1922-06-01", 48.8566, 2.3522, "塞纳", "省", "CC BY 4.0"),
    ("1870-06-01", 49.119, 6.175, "摩泽尔", "省", "CC BY 4.0"),
    ("1897-07-01", 55.7558, 37.6173, "莫斯科省", "省", "CC BY 4.0"),
    ("1926-07-01", 55.7558, 37.6173, "莫斯科省", "省", "CC BY 4.0"),
    ("1934-06-01", 52.23, 21.012, "华沙市", "省", "PDDL 1.0"),
    ("1936-06-01", 41.903, 12.496, "罗马", "省", "CC BY 3.0"),
    ("1850-06-01", 51.507, -0.128, "米德尔塞克斯", "郡", "Historic Counties Trust"),
    ("1930-06-01", 40.4168, -3.7038, "马德里", "省", "CC BY 4.0"),
    ("1925-06-01", 28.4637, -16.2518, "加那利", "省", "CC BY 4.0"),
    ("1930-06-01", 28.4637, -16.2518, "圣克鲁斯-德特内里费", "省", "CC BY 4.0"),
    ("1912-06-01", 51.5074, -0.1278, "伦敦", "行政郡", "CC BY-SA 4.0"),
]
for day, lat, lon, name, kind, license_name in cases:
    row = place(day, lat, lon)
    check(
        f"{day} {name}",
        row["status"] == "draw" and row.get("name") == name and row.get("kind") == kind
        and license_name in (row.get("license") or "") and "不画今天的省界" in (row.get("note") or "")
        and "今天的省" not in (row.get("name") or ""),
        row,
    )

for day, lat, lon, label in (
    ("1872-06-01", 49.119, 6.175, "梅斯"),
    ("1860-06-01", 48.8566, 2.3522, "巴黎"),
    ("1862-07-01", 41.903, 12.496, "罗马"),
    ("1900-06-01", 51.507, -0.128, "伦敦"),
    ("1880-06-01", 40.4168, -3.7038, "马德里"),
    ("1966-06-01", 51.5074, -0.1278, "伦敦"),
    ("1930-06-01", 44.426, 26.102, "布加勒斯特"),
    ("1930-06-01", 44.817, 20.457, "贝尔格莱德"),
    ("1950-06-01", 39.9042, 116.4074, "北京"),
):
    row = place(day, lat, lon)
    check(
        f"{day} {label} 省界待考",
        row["status"] == "none" and row.get("name") is None and "省界待考" in (row.get("note") or "")
        and "不画今天的省界" in (row.get("note") or ""),
        row,
    )

early = layer("1860-06-01")
mid = layer("1922-06-01")
check("1860 不画法国省", all(item.get("nominal") != "法国" for item in early["items"]), early["total"])
check("1922 画出塞纳", any(item.get("name") == "塞纳" for item in mid["items"]), mid["total"])
check("1922 不把法兰西岛当省", all("法兰西岛" not in (item.get("name") or "") for item in mid["items"]), "")
names = {item["name"] for item in layer("1914-06-01")["items"]}
check("1914 有东普鲁士", "东普鲁士" in names, "")
check("1914 没有用今天的联邦州顶上巴伐利亚", "巴伐利亚" not in names, "")

ref = get("/api/admin1_ref", west=-10, south=35, east=40, north=60, zoom=6)
check("admin1_ref 仍不返回今天的省界", ref.get("features") == [] and "不是历史省界" in (ref.get("note") or ""), ref.get("note"))

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
