"""第十批：克什米尔、锡亚琴、河西岸、加沙、台湾。实控、声索、承认分开。

不改底图政权名。用法：WHA_PORT=8792 python3 tools/accept/next_batch10.py
"""
import json, os, sys, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=300))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:300])
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
    return " ".join((r.get("party") or {}).get("zh", "") + " " + r.get("text", "") for r in rs)


def ids(date, prefix):
    return [i["id"] for i in feats(date) if i["id"].startswith(prefix)]


# 底图政权名不改
check("1975 斯利那加底图仍是印度", "印度" in regime("1975-06-01", 34.08, 74.80), regime("1975-06-01", 34.08, 74.80))
check("1975 台北底图仍是中华民国", "中华民国" in regime("1975-06-01", 25.03, 121.56), regime("1975-06-01", 25.03, 121.56))

# 克什米尔：1971 年以前的线不回贴
h = hit("1965-06-01", 34.08, 74.80)
c = text(rows(h, "kashmir_india", "control"))
check("1965 斯利那加不填今天的行政界", "不填色" in c and "不回贴" in c, c)
check("1965 没有印度管治填色", "kashmir_india-control" not in ids("1965-06-01", "kashmir"), ids("1965-06-01", "kashmir"))
h = hit("1972-07-01", 34.08, 74.80)
check("1972-07-01 西姆拉协定还没签", "不填色" in text(rows(h, "kashmir_india", "control")), text(rows(h, "kashmir_india", "control")))

h = hit("1972-07-02", 34.08, 74.80)
c, cl = text(rows(h, "kashmir_india", "control")), text(rows(h, "kashmir_india", "claim"))
check("1972-07-02 斯利那加实控印度", "印度" in c and "巴基斯坦" not in c, c)
check("1972-07-02 斯利那加声索有巴基斯坦且不是实控", "巴基斯坦" in cl and "不是实控" in cl and "印度" in cl, cl)
check("1972-07-02 有印度填色和巴基斯坦虚线", "kashmir_india-control" in ids("1972-07-02", "kashmir_india") and "kashmir_india-claim" in ids("1972-07-02", "kashmir_india"), ids("1972-07-02", "kashmir"))

h = hit("1972-07-02", 34.37, 73.47)
c, cl = text(rows(h, "kashmir_pakistan", "control")), text(rows(h, "kashmir_pakistan", "claim"))
check("1972-07-02 穆扎法拉巴德实控巴基斯坦", "巴基斯坦" in c and "印度" not in c, c)
check("1972-07-02 穆扎法拉巴德有印度声索且不是实控", "印度" in cl and "不是实控" in cl, cl)

# 阿克赛钦样本点不落进印度管治轮廓
check("1962 阿克赛钦样本点不命中印度管治块", not any(x["id"] == "kashmir_india" for x in hit("1962-11-01", 35.2, 79.0)), [x["id"] for x in hit("1962-11-01", 35.2, 79.0)])

# 锡亚琴
h = hit("1984-04-12", 35.4, 77.0)
check("1984-04-12 锡亚琴不填", "不填色" in text(rows(h, "siachen", "control")), text(rows(h, "siachen", "control")))
h = hit("1984-04-13", 35.4, 77.0)
check("1984-04-13 锡亚琴实控印度、巴基斯坦声索不是实控", "印度" in text(rows(h, "siachen", "control")) and "不是实控" in text(rows(h, "siachen", "claim")) and "不是盐岭" in text(rows(h, "siachen", "claim")), text(rows(h, "siachen", "claim")))

# 河西岸 / 加沙
h = hit("1955-06-01", 31.90, 35.20)
c, cl = text(rows(h, "west_bank", "control")), text(rows(h, "west_bank", "claim"))
check("1955 拉马拉实控约旦", "由约旦控制" in c and "由以色列" not in c, c)
check("1955 拉马拉还没有巴勒斯坦宣言虚线", "巴勒斯坦" not in cl and "约旦" in cl, cl)
check("2010 东耶路撒冷不落入河西岸轮廓", not any(x["id"] == "west_bank" for x in hit("2010-06-01", 31.778, 35.235)), "ej")

h = hit("1960-06-01", 31.52, 34.47)
check("1960 加沙城实控埃及且没有正式并入", "埃及" in text(rows(h, "gaza", "control")) and "没有把加沙正式并入" in text(rows(h, "gaza", "control")), text(rows(h, "gaza", "control")))
h = hit("2000-06-01", 31.52, 34.47)
check("2000 加沙是以色列军事占领不是主权", "以色列" in text(rows(h, "gaza", "control")) and "不是主权" in text(rows(h, "gaza", "control")), text(rows(h, "gaza", "control")))
h = hit("2010-06-01", 31.52, 34.47)
c, rec = text(rows(h, "gaza", "control")), text(rows(h, "gaza", "recognition"))
check("2010 加沙带内是哈马斯且边界仍由以色列控制", "哈马斯" in c and "以色列仍控制边界" in c, c)
check("2010 加沙还没有 67/19", "242" in rec and "67/19" not in rec, rec)
h = hit("2013-06-01", 31.90, 35.20)
rec = text(rows(h, "west_bank", "recognition"))
check("2013 河西岸承认写 67/19、138，且不是联合国会员", "67/19" in rec and "138" in rec and "不是联合国会员" in rec, rec)
h = hit("2024-06-01", 31.52, 34.47)
check("2024 加沙不填并标待考", "待考" in text(rows(h, "gaza", "control")) and "gaza-control" not in ids("2024-06-01", "gaza"), text(rows(h, "gaza", "control")))

# 台湾：声索虚线，不另铺实控色，2758 不写成领土地位判决
h = hit("1948-06-01", 25.03, 121.56)
check("1948 台北实控中华民国且中华人民共和国还没有成立", "中华民国" in text(rows(h, "taiwan", "control")) and "还没有成立" in text(rows(h, "taiwan", "claim")), text(rows(h, "taiwan", "claim")))
check("1948 台湾不画虚线", "taiwan-claim" not in ids("1948-06-01", "taiwan") and "taiwan-control" not in ids("1948-06-01", "taiwan"), ids("1948-06-01", "taiwan"))
h = hit("1971-10-24", 25.03, 121.56)
check("1971-10-24 2758 还没通过", "2758" not in text(rows(h, "taiwan", "recognition")) and "中华民国的代表" in text(rows(h, "taiwan", "recognition")), text(rows(h, "taiwan", "recognition")))
h = hit("1971-10-25", 25.03, 121.56)
rec = text(rows(h, "taiwan", "recognition"))
cl = text(rows(h, "taiwan", "claim"))
check("1971-10-25 写 2758 且正文没有写台湾的领土地位", "2758" in rec and "没有写台湾的领土地位" in rec and "待考" in rec, rec)
check("1971-10-25 声索有中华人民共和国且不是实控，大陆不画", "中华人民共和国" in cl and "不是实控" in cl and "不画" in cl, cl)
check("1971-10-25 只有声索虚线", ids("1971-10-25", "taiwan") == ["taiwan-claim"], ids("1971-10-25", "taiwan"))
check("2020 马祖点不落入这块轮廓", hit("2020-06-01", 26.16, 119.95) == [] or not any(x["id"] == "taiwan" for x in hit("2020-06-01", 26.16, 119.95)), [x["id"] for x in hit("2020-06-01", 26.16, 119.95)])

# 福克兰：登陆不等于承认；南乔治亚不在轮廓里
h = hit("1982-04-01", -51.70, -57.85)
check("1982-04-01 斯坦利实控英国", "英国" in text(rows(h, "falklands", "control")) and "阿根廷" not in text(rows(h, "falklands", "control")), text(rows(h, "falklands", "control")))
h = hit("1982-04-02", -51.70, -57.85)
check("1982-04-02 斯坦利实控阿根廷、英国声索还在", "阿根廷" in text(rows(h, "falklands", "control")) and "英国" in text(rows(h, "falklands", "claim")), text(rows(h, "falklands", "claim")))
h = hit("1982-06-14", -51.70, -57.85)
rec = text(rows(h, "falklands", "recognition"))
check("1982-06-14 实控回到英国且 2065 没有把主权判给阿根廷", "英国" in text(rows(h, "falklands", "control")) and "2065" in rec and "没有把主权判给阿根廷" in rec, rec)
check("南乔治亚不落入福克兰轮廓", not any(x["id"] == "falklands" for x in hit("1982-04-10", -54.28, -36.5)), "sg")

# 北方四岛：不含得抚以北；1956 年没有交还
check("1940 择捉还没有这层争议填色", not any(x["id"] == "kuril_south" for x in hit("1940-06-01", 45.05, 147.8)), "1940")
h = hit("1990-06-01", 45.05, 147.8)
check("1990 择捉实控苏联不是俄罗斯", "苏联" in text(rows(h, "kuril_south", "control")) and "俄罗斯" not in text(rows(h, "kuril_south", "control")), text(rows(h, "kuril_south", "control")))
h = hit("2000-06-01", 45.05, 147.8)
check("2000 择捉实控俄罗斯、日本声索且 1956 年没有交还", "俄罗斯" in text(rows(h, "kuril_south", "control")) and "日本" in text(rows(h, "kuril_south", "claim")) and "没有交还" in text(rows(h, "kuril_south", "recognition")), text(rows(h, "kuril_south", "recognition")))
check("得抚不落入北方四岛", not any(x["id"] == "kuril_south" for x in hit("2000-06-01", 45.9, 149.8)), "urup")

# 阿尔萨斯-洛林：实控、法理生效日分开；贝尔福和南锡不在内
h = hit("1880-06-01", 48.58, 7.75)
check("1880 斯特拉斯堡实控德意志帝国", "德意志帝国" in text(rows(h, "alsace_lorraine", "control")), text(rows(h, "alsace_lorraine", "control")))
check("1880 有法国主张虚线", "alsace_lorraine-claim" in ids("1880-06-01", "alsace_lorraine"), ids("1880-06-01", "alsace_lorraine"))
h = hit("1918-11-11", 48.58, 7.75)
check("1918-11-11 斯特拉斯堡不填成同一天易手", "不填色" in text(rows(h, "alsace_lorraine", "control")), text(rows(h, "alsace_lorraine", "control")))
h = hit("1942-06-01", 48.58, 7.75)
check("1942 阿尔萨斯不填且没有正式吞并", "不填色" in text(rows(h, "alsace_lorraine", "control")) and "没有正式吞并" in text(rows(h, "alsace_lorraine", "control")), text(rows(h, "alsace_lorraine", "control")))
check("南锡和贝尔福不落入阿尔萨斯-洛林轮廓", hit("1880-06-01", 48.69, 6.18) == [] and not any(x["id"] == "alsace_lorraine" for x in hit("1880-06-01", 47.64, 6.86)), "nancy")

# 西沙填色，南沙不填，黄岩岛不在内
h = hit("1970-06-01", 16.83, 112.33)
check("1970 西沙不把整群填成一方", "不把整群填成一方" in text(rows(h, "paracel", "control")) and "paracel-control" not in ids("1970-06-01", "paracel"), text(rows(h, "paracel", "control")))
h = hit("1974-01-20", 16.83, 112.33)
check("1974-01-20 西沙实控中华人民共和国、越南声索不是实控", "中华人民共和国" in text(rows(h, "paracel", "control")) and "不是实控" in text(rows(h, "paracel", "claim")), text(rows(h, "paracel", "claim")))
sp = area("2000-06-01", "spratly")
check("南沙不填色且不是九段线", sp["rows"] and "不填" in text(sp["rows"]) and "不是九段线" in text(sp["rows"]) and "spratly-control" not in ids("2000-06-01", "spratly"), text(sp["rows"])[:180])
check("黄岩岛不落入南沙轮廓", not any(x["id"] == "spratly" for x in hit("2000-06-01", 15.15, 117.75)), "scarborough")

# 没有几何的：不画
for name, date, needle in (
    ("aksai", "1960-06-01", "待考"),
    ("south_tibet", "1950-06-01", "不画"),
    ("saar", "1925-06-01", "国际联盟"),
    ("danzig", "1925-06-01", "自由市"),
    ("nagorno_karabakh", "2000-06-01", "不填色"),
    ("transnistria", "2000-06-01", "俄罗斯也没有承认"),
):
    got = area(date, name)
    blob = text(got["rows"])
    check(f"{date} {name} 不画且写到要点", got["probe"] is None and needle in blob and not any(i["area"] == name for i in feats(date)), blob[:160])
nk = area("2024-01-01", "nagorno_karabakh")
check("2024-01-01 纳卡机构停止、实控记阿塞拜疆、仍然不画", nk["probe"] is None and "阿塞拜疆" in text(nk["rows"]) and "2024-01-01" in text(nk["rows"]), text(nk["rows"])[:180])

print(f"FAILS {len(fails)}")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
