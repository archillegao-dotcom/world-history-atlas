"""第二批：实控 / 声索 / 承认。克里米亚 2013、2014-04、2022，以及几个争议区。

底图政权名保持原断言：2015-07-01 辛菲罗波尔仍是俄罗斯，1980-07-01 凯里尼亚仍能对上土族邦或土耳其。
用法：WHA_PORT=8792 python3 tools/accept/next_batch2.py
"""
import json, os, sys, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=300))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:240])
    if not cond:
        fails.append(label)


def regime(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    d = get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=p["fid"])
    return (d.get("state") or {}).get("name") or ""


def hit(date, lat, lon):
    return get("/api/layers/status_layers", date=date, lat=lat, lon=lon, rows=1)["hits"]


def area(date, name):
    return get("/api/layers/status_layers", date=date, area=name, rows=1)["area"]


def feats(date):
    return get("/api/layers/status_layers", date=date)["items"]


def rows(hits, aid, role):
    h = next(x for x in hits if x["id"] == aid)
    return [r for r in h["rows"] if r["role"] == role]


def text(rs):
    return " ".join((r.get("party") or {}).get("zh", "") + " " + r.get("text", "") + " " + (r.get("point") or "") for r in rs)


# 底图政权名不改
check("2013 辛菲罗波尔底图是乌克兰", "乌克兰" in regime("2013-06-01", 44.95, 34.1) and "俄罗斯" not in regime("2013-06-01", 44.95, 34.1), regime("2013-06-01", 44.95, 34.1))
check("2014-04 辛菲罗波尔底图仍是俄罗斯", "俄罗斯" in regime("2014-04-01", 44.95, 34.1), regime("2014-04-01", 44.95, 34.1))
check("2015-07-01 辛菲罗波尔底图仍是俄罗斯", "俄罗斯" in regime("2015-07-01", 44.95, 34.1), regime("2015-07-01", 44.95, 34.1))
check("2020 辛菲罗波尔底图仍是俄罗斯", "俄罗斯" in regime("2020-06-01", 44.95, 34.1), regime("2020-06-01", 44.95, 34.1))
check("2022-06 辛菲罗波尔底图仍是俄罗斯", "俄罗斯" in regime("2022-06-01", 44.95, 34.1), regime("2022-06-01", 44.95, 34.1))
k1980 = regime("1980-07-01", 35.34, 33.32)
check("1980 凯里尼亚底图仍是土族邦、土耳其或北塞浦路斯", any(s in k1980 for s in ("土族邦", "土耳其", "北塞浦路斯")), k1980)

# 克里米亚三行
h = hit("2013-06-01", 44.95, 34.1)
check("2013 只命中克里米亚", [x["id"] for x in h] == ["crimea"], [x["id"] for x in h])
c, cl, rec = text(rows(h, "crimea", "control")), text(rows(h, "crimea", "claim")), text(rows(h, "crimea", "recognition"))
check("2013 实控是乌克兰", "乌克兰" in c and "俄罗斯" not in c, c)
check("2013 声索是乌克兰", "乌克兰" in cl and "俄罗斯" not in cl, cl)
check("2013 承认是乌克兰且还没有 68/262", "乌克兰" in rec and "68/262" not in rec, rec)
check("2013 地图没有克里米亚声索虚线", not any(i["id"] == "crimea-claim" for i in feats("2013-06-01")), "dash")

h = hit("2014-03-17", 44.95, 34.1)
c = text(rows(h, "crimea", "control"))
check("2014-03-17 整片还不标成俄罗斯实控", "乌克兰" in c and "俄罗斯" not in c, c)

h = hit("2014-03-20", 44.95, 34.1)
c, cl, rec = text(rows(h, "crimea", "control")), text(rows(h, "crimea", "claim")), text(rows(h, "crimea", "recognition"))
check("2014-03-20 实控俄罗斯", "俄罗斯" in c, c)
check("2014-03-20 声索仍有乌克兰", "乌克兰" in cl, cl)
check("2014-03-20 决议还没有通过", "还没有通过" in rec and "68/262" not in rec, rec)

h = hit("2014-04-01", 44.95, 34.1)
c, cl, rec = text(rows(h, "crimea", "control")), text(rows(h, "crimea", "claim")), text(rows(h, "crimea", "recognition"))
check("2014-04 实控俄罗斯且该点在前线内", "俄罗斯" in c and "评估控制区内" in c and "不在当日" not in c, c)
check("2014-04 声索同时有乌克兰和俄罗斯", "乌克兰" in cl and "俄罗斯" in cl, cl)
check("2014-04 承认写 68/262 与 2014-03-27", "68/262" in rec and "2014-03-27" in rec and "乌克兰" in rec, rec)
ids = [i["id"] for i in feats("2014-04-01")]
check("2014-04 有声索虚线、没有第二层实控填色", "crimea-claim" in ids and "crimea-control" not in ids, ids)

h = hit("2022-06-01", 44.95, 34.1)
c, cl, rec = text(rows(h, "crimea", "control")), text(rows(h, "crimea", "claim")), text(rows(h, "crimea", "recognition"))
check("2022-06 克里米亚实控俄罗斯", "俄罗斯" in c and "评估控制区内" in c, c)
check("2022-06 克里米亚声索仍有乌克兰", "乌克兰" in cl, cl)
check("2022-06 克里米亚承认仍是 68/262，还没有 ES-11/4", "68/262" in rec and "ES-11/4" not in rec, rec)

# 四州：宣布不等于实控，也不等于承认
h = hit("2022-09-28", 46.64, 32.61)
cl = text(rows(h, "ua_four", "claim"))
check("2022-09-28 赫尔松声索还没有俄罗斯宣布", "乌克兰" in cl and "俄罗斯" not in cl, cl)
h = hit("2022-09-29", 46.64, 32.61)
cl = text(rows(h, "ua_four", "claim"))
rec = text(rows(h, "ua_four", "recognition"))
check("2022-09-29 赫尔松出现俄罗斯宣布的声索", "俄罗斯" in cl and "乌克兰" in cl and "不是实控" in cl, cl)
check("2022-09-29 承认决议还没有通过", "还没有通过" in rec, rec)
h = hit("2022-12-01", 46.64, 32.61)
c = text(rows(h, "ua_four", "control"))
cl = text(rows(h, "ua_four", "claim"))
rec = text(rows(h, "ua_four", "recognition"))
check("2022-12-01 赫尔松城不在评估控制区内", "不在当日" in c and "四个州整片" in c, c)
check("2022-12-01 声索仍是乌克兰加俄罗斯宣布", "乌克兰" in cl and "俄罗斯" in cl, cl)
check("2022-12-01 承认写 ES-11/4 与 143", "ES-11/4" in rec and "143" in rec and "不等于承认" in rec, rec)
check("2022-06 基辅不落入四州", hit("2022-06-01", 50.45, 30.52) == [], "kyiv")

# 顿巴斯：州界不是接触线
h = hit("2014-06-01", 48.00, 37.80)
c = text(rows(h, "donbas", "control"))
check("2014-06 顿涅茨克不画逐日实控", "不画实控" in c, c)
h = hit("2020-06-01", 47.10, 37.55)
c = text(rows(h, "donbas", "control"))
check("2020 马里乌波尔在州内但不在当时的评估控制区", "不是两个州全境" in c and "不在当日" in c, c)

# 其他争议区
ab = area("2010-06-01", "abkhazia")
ab_t = text(ab["rows"])
check("2010 阿布哈兹声索有格鲁吉亚、承认写 2008-08-26 且其他国家待考", "格鲁吉亚" in ab_t and "2008-08-26" in ab_t and "待考" in ab_t, ab_t)
check("2008-08-25 阿布哈兹这一层还没开始", area("2008-08-25", "abkhazia")["rows"] == [], "before")
ids = [i["id"] for i in feats("2010-06-01")]
check("2010 阿布哈兹既有填色也有虚线", "abkhazia-control" in ids and "abkhazia-claim" in ids, ids)

so = area("2010-06-01", "south_ossetia")
check("南奥塞梯不画并标待考", so["probe"] is None and "待考" in text(so["rows"]) and not any(i["area"] == "south_ossetia" for i in feats("2010-06-01")), text(so["rows"])[:160])

h = hit("1980-07-01", 35.34, 33.32)
c, cl, rec = text(rows(h, "northern_cyprus", "control")), text(rows(h, "northern_cyprus", "claim")), text(rows(h, "northern_cyprus", "recognition"))
check("1980 北部实控是土族邦", "土族邦" in c, c)
check("1980 声索有塞浦路斯", "塞浦路斯" in cl, cl)
check("1980 541 还没通过", "待考" in rec and "541" not in rec, rec)
h = hit("2020-06-01", 35.34, 33.32)
c, rec = text(rows(h, "northern_cyprus", "control")), text(rows(h, "northern_cyprus", "recognition"))
check("2020 北部实控是北塞浦路斯、承认写 541", "北塞浦路斯" in c and "541" in rec and "土耳其" in rec, c + " || " + rec)

g = area("2000-06-01", "golan")
check("2000 戈兰不画，有叙利亚声索和 497，还没有美国 2019 承认", g["probe"] is None and "叙利亚" in text(g["rows"]) and "497" in text(g["rows"]) and "2019-03-25" not in text(g["rows"]) and "待考" in text(g["rows"]), text(g["rows"])[:200])
g = area("2020-06-01", "golan")
check("2020 戈兰写美国 2019-03-25 承认且不是联合国承认", "2019-03-25" in text(g["rows"]) and "不是联合国的承认" in text(g["rows"]) and "497" in text(g["rows"]), text(g["rows"])[:220])

ws = " ".join(i["id"] for i in feats("2020-06-01") if i["area"] == "western_sahara")
wst = text(area("2020-06-01", "western_sahara")["rows"])
check("西撒哈拉只有声索虚线，实控分界待考", ws == "western_sahara-claim" and "待考" in wst and "摩洛哥" in wst and "萨赫拉维" in wst, ws + " " + wst[:160])

k = area("2007-06-01", "kosovo")
check("2007 科索沃是 1244 临时行政，不把塞尔维亚写成当时的声索方", "1244" in text(k["rows"]) and "南斯拉夫联盟共和国" in text(k["rows"]) and not any((r.get("party") or {}).get("zh") == "塞尔维亚" for r in k["rows"]), text(k["rows"])[:180])
k = area("2010-08-01", "kosovo")
check("2010-08 科索沃声索有塞尔维亚，咨询意见不是承认", "塞尔维亚" in text(k["rows"]) and "咨询意见" in text(k["rows"]) and "不是承认" in text(k["rows"]) and "待考" in text(k["rows"]), text(k["rows"])[:200])

print(f"FAILS {len(fails)}")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
