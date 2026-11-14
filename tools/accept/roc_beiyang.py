"""北洋这一批：大致战线、县城点、北京政府几件条约。

不改 war_audit.py 的 86 条。用法：WHA_PORT=8792 python3 tools/accept/roc_beiyang.py
"""
import json, os, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.roc_beiyang import bundle

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []
ROOT = Path(__file__).resolve().parents[2]


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:300])
    if not cond:
        fails.append(label)


def get(path, **kw):
    q = "?" + urllib.parse.urlencode(kw) if kw else ""
    return json.load(urllib.request.urlopen(B + path + q, timeout=180))


def ids_on(day):
    return {row["id"] for row in bundle(ROOT / "data", day)["fronts"]}


check("7月16日前不画直皖走廊", "zhiwan-jingfeng" not in ids_on("1920-07-15"), ids_on("1920-07-15"))
check("7月16日起画京奉走廊", "zhiwan-jingfeng" in ids_on("1920-07-18"), ids_on("1920-07-18"))
check("7月24日起不画直皖走廊", "zhiwan-jingfeng" not in ids_on("1920-07-24"), "")
check("9月14日不画第二次直奉", "zhifeng2-chaoyang" not in ids_on("1924-09-14"), "")
check("9月15日只画朝阳方向", ids_on("1924-09-15") == {"zhifeng2-chaoyang", "jiangzhe-huning"}, ids_on("1924-09-15"))
check("10月19日画京奉总攻，江浙走廊还在",
      {"zhifeng2-jingfeng", "zhifeng2-chaoyang", "jiangzhe-huning"} <= ids_on("1924-10-19"), ids_on("1924-10-19"))
check("10月20日起这三条线都撤下", not ids_on("1924-10-20"), ids_on("1924-10-20"))
seats = {row["id"] for row in bundle(ROOT / "data", "1925-06-01")["seats"]}
check("1925-06-01 安次是待考点，不是县界", "anci-gap" in seats and "anci" not in seats, seats)
check("1925-06-01 没有1920或1924的战线", not ids_on("1925-06-01"), "")
check("12月24日不画护国点线", "yuehan-1922" not in ids_on("1915-12-25") and "kunming-1915" not in {s["id"] for s in bundle(ROOT / "data", "1915-12-24")["seats"]}, "")
check("12月25日有昆明点，没有铁路", "kunming-1915" in {s["id"] for s in bundle(ROOT / "data", "1915-12-25")["seats"]} and not ids_on("1915-12-25"), "")
check("12月26日起不留护国点", "kunming-1915" not in {s["id"] for s in bundle(ROOT / "data", "1915-12-26")["seats"]}, "")
check("5月12日不画粤汉走廊", "yuehan-1922" not in ids_on("1922-05-12"), "")
check("5月13日画粤汉走廊", ids_on("1922-05-13") == {"yuehan-1922"}, ids_on("1922-05-13"))
check("5月14日起不留粤汉走廊", "yuehan-1922" not in ids_on("1922-05-14"), "")
check("2月3日不画淞沪铁路", not ids_on("1932-02-03"), "")
check("2月4日只画沪宁和沪杭", ids_on("1932-02-04") == {"huning-1932", "huhang-1932"}, ids_on("1932-02-04"))
check("2月5日起不留淞沪铁路", not ids_on("1932-02-05"), "")


def place(date, lat, lon):
    return get("/api/modules/roc_admin", date=date, lat=lat, lon=lon)


bj = place("1920-07-18", 39.9042, 116.4074)
check("1920-07-18 北京仍是直隶，实控不是皖系独占",
      bj["place"]["name"] == "直隶" and bj["place"]["actual"] == "实控待考", bj["place"])
check("面板写直皖和不是县界",
      any(w["id"] == "zhiwan-1920" for w in bj["wars"]) and "不是县界" in json.dumps(bj, ensure_ascii=False),
      [w["name"] for w in bj["wars"]])
layer = get("/api/layers/roc_provinces", date="1920-07-18")
check("图层在7月18日有京奉走廊", any(f["id"] == "zhiwan-jingfeng" for f in layer["fronts"]), [f["id"] for f in layer["fronts"]])
check("许可字段仍是省界的 CC0", layer.get("license") == "CC0 1.0" and "CHGIS" in (layer.get("note") or ""), layer.get("license"))
check("1926-07-01 北京实控仍是待考，不写成奉系",
      place("1926-07-01", 39.9042, 116.4074)["place"]["actual"] == "实控待考", "")
km = place("1915-12-25", 25.067, 102.695)
check("1915-12-25 昆明实控仍待考，面板有护国",
      km["place"]["name"] == "云南" and km["place"]["actual"] == "实控待考" and any(w["id"] == "huguo-1915" for w in km["wars"]),
      km["place"])
nx = place("1922-05-13", 25.214, 114.3)
check("1922-05-13 南雄不改全省实控，面板有粤汉",
      nx["place"]["actual"] == "实控待考" and any(f["id"] == "yuehan-1922" for f in nx["fronts"]) and "不是县界" in json.dumps(nx, ensure_ascii=False),
      nx["place"])
sh = place("1932-02-04", 31.233, 121.477)
check("1932-02-04 上海仍是南京国民政府，并有沪宁",
      sh["place"]["name"] == "江苏" and sh["place"]["actual"] == "南京国民政府" and any(f["id"] == "huning-1932" for f in sh["fronts"]),
      sh["place"])


def names(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc["polity"]
    body = get("/api/modules/spirits", date=date, snap=loc["snapshot"], fid=p["fid"])
    return [row.get("name") or "" for row in body.get("dated", []) + body.get("open", []) + body.get("pending", []) + body.get("never", [])]


def has(rows, text):
    return any(text in row for row in rows)


bj1915 = names("1915-05-25", 39.9, 116.4)
check("1915-05-25 看得到两件民四条约", has(bj1915, "山东省") and has(bj1915, "南满洲"), bj1915)
check("1915-05-24 还看不到这两件", not has(names("1915-05-24", 39.9, 116.4), "山东省"), "")
bj1922 = names("1922-02-06", 39.9, 116.4)
check("1922-02-06 看得到九国公约和山东悬案", has(bj1922, "九国") and has(bj1922, "山东悬案"), bj1922)
check("1924-05-30 还看不到中俄协定", not has(names("1924-05-30", 39.9, 116.4), "中俄解决悬案"), "")
check("1924-05-31 看得到中俄协定", has(names("1924-05-31", 39.9, 116.4), "中俄解决悬案"), "")

loc = get("/api/locate", date="1919-06-28", lat=39.9, lon=116.4)
p = loc["polity"]
ev = get("/api/modules/events", date="1919-06-28", snap=loc["snapshot"], fid=p["fid"])
titles = [row.get("title") or "" for row in ev.get("items") or []]
check("1919-06-28 事件栏有拒签", any("拒绝签署" in t for t in titles), titles[:8])
check("拒签不作为生效条约插进条约栏", not has(names("1919-06-28", 39.9, 116.4), "拒绝签署"), "")

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
