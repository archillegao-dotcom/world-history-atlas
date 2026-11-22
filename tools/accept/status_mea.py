"""中东、非洲、南亚：实控 / 声索 / 承认按日期分开。

不改克里米亚那一批的断言。缺几何的不画。实控不等于法理归属。
用法：WHA_PORT=8792 python3 tools/accept/status_mea.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=300))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:300])
    if not cond:
        fails.append(label)


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
    return " ".join((r.get("party") or {}).get("zh", "") + " " + (r.get("text") or "") for r in rs)


def ids_of(date, aid):
    return [i["id"] for i in feats(date) if i["area"] == aid]


# 索马里兰：五天独立、合并、1991 事实控制、2025-12-26 才有以色列承认
h = hit("1960-06-28", 9.56, 44.065)
c, cl, rec = text(rows(h, "somaliland", "control")), text(rows(h, "somaliland", "claim")), text(rows(h, "somaliland", "recognition"))
check("1960-06-28 索马里兰是独立的五天", "索马里兰国" in c and "1991" not in c, c)
check("1960-06-28 承认国数待考", "待考" in rec and "以色列" not in rec, rec)
check("1960-06-28 不填色", "somaliland-control" not in ids_of("1960-06-28", "somaliland"), ids_of("1960-06-28", "somaliland"))

h = hit("1960-07-02", 9.56, 44.065)
c = text(rows(h, "somaliland", "control"))
check("1960-07-02 已并入索马里", "索马里共和国" in c and "索马里兰国" not in c, c)

h = hit("1991-05-17", 9.56, 44.065)
c = text(rows(h, "somaliland", "control"))
check("1991-05-17 还没有布尔奥大会后的事实共和国", "索马里共和国" in c and "布尔奥" not in c, c)

h = hit("2000-06-01", 9.56, 44.065)
c, cl, rec = text(rows(h, "somaliland", "control")), text(rows(h, "somaliland", "claim")), text(rows(h, "somaliland", "recognition"))
check("2000 实控是索马里兰且大致", "索马里兰" in c and "大致" in c, c)
check("2000 声索仍有索马里", "索马里" in cl and "索马里兰" in cl, cl)
check("2000 没有联合国会员承认", "没有联合国会员" in rec and "以色列" not in rec, rec)
ids = ids_of("2000-06-01", "somaliland")
check("2000 有填色也有声索虚线", "somaliland-control" in ids and "somaliland-claim" in ids, ids)
check("2000 摩加迪沙不是索马里兰", hit("2000-06-01", 2.046, 45.318) == [] or all(x["id"] != "somaliland" for x in hit("2000-06-01", 2.046, 45.318)), "mog")

h = hit("2025-12-25", 9.56, 44.065)
check("2025-12-25 还没有以色列承认", "以色列" not in text(rows(h, "somaliland", "recognition")), text(rows(h, "somaliland", "recognition"))[:180])
h = hit("2025-12-26", 9.56, 44.065)
rec = text(rows(h, "somaliland", "recognition"))
check("2025-12-26 以色列承认但不是联合国会籍", "以色列" in rec and "不是联合国会籍" in rec and "索马里兰" in text(rows(h, "somaliland", "control")), rec[:220])

# 厄立特里亚：联邦、取消日不择一、1991 事实管治、1993-05-24 独立还不是会员
h = hit("1960-06-01", 15.322, 38.925)
c, cl = text(rows(h, "eritrea_pre1993", "control")), text(rows(h, "eritrea_pre1993", "claim"))
check("1960 厄立特里亚是联邦不是普通省", "联邦" in c and "普通" in c and "埃塞俄比亚" in cl, c + " || " + cl)
check("1960 厄立特里亚有填色", "eritrea_pre1993-control" in ids_of("1960-06-01", "eritrea_pre1993"), ids_of("1960-06-01", "eritrea_pre1993"))
check("1960 亚的斯亚贝巴不是这层", all(x["id"] != "eritrea_pre1993" for x in hit("1960-06-01", 9.03, 38.747)), "addis")

h = hit("1962-11-14", 15.322, 38.925)
c = text(rows(h, "eritrea_pre1993", "control"))
check("1962-11-14 取消自治的日子不择一且不填色", "不择一" in c and "eritrea_pre1993-control" not in ids_of("1962-11-14", "eritrea_pre1993"), c)

h = hit("1988-06-01", 15.322, 38.925)
c = text(rows(h, "eritrea_pre1993", "control"))
check("1988 不把国境填成某一方全部占有", "不把今国境填成" in c and "eritrea_pre1993-control" not in ids_of("1988-06-01", "eritrea_pre1993"), c)

h = hit("1992-06-01", 15.322, 38.925)
c, rec = text(rows(h, "eritrea_pre1993", "control")), text(rows(h, "eritrea_pre1993", "recognition"))
check("1992 是解放阵线事实管治", "人民解放阵线" in c and "不是已经加入联合国" in c, c)
check("1992 还不是会员", "不是联合国会员" in rec, rec)

h = hit("1993-05-24", 15.322, 38.925)
rec = text(rows(h, "eritrea_pre1993", "recognition"))
check("1993-05-24 独立但 28 日才入联", "1993-05-24" in rec and "还不是会员" in rec and "eritrea_pre1993-control" not in ids_of("1993-05-24", "eritrea_pre1993"), rec[:200])
h = hit("1993-05-28", 15.322, 38.925)
check("1993-05-28 写 47/230", "47/230" in text(rows(h, "eritrea_pre1993", "recognition")), text(rows(h, "eritrea_pre1993", "recognition"))[:160])

# 没有几何的：比夫拉、阿卜耶伊、哈拉伊卜、黎巴嫩、叙利亚、锡亚琴、飞地、奥加登、奥祖、哈塔伊
b = area("1968-06-01", "biafra")
bt = text(b["rows"])
check("1968 比夫拉不画，四国承认，海地不写成已核实", b["probe"] is None and "不画" in bt and "坦桑尼亚" in bt and "不把它算成已核实" in bt and not any(i["area"] == "biafra" for i in feats("1968-06-01")), bt[:200])
check("1970-01-15 比夫拉投降", "投降" in text(area("1970-01-15", "biafra")["rows"]), text(area("1970-01-15", "biafra")["rows"])[:120])

ab = area("2011-06-01", "abyei")
abt = text(ab["rows"])
check("2011-06 阿卜耶伊不画，苏丹军队在镇上，1990 号决议还没写", ab["probe"] is None and "不画" in abt and "苏丹武装部队" in abt and "1990" not in abt and "2009-07-22" in abt, abt[:220])
check("2011-07 阿卜耶伊写 1990 且没有并进南苏丹", "1990" in text(area("2011-07-01", "abyei")["rows"]) and "没有把阿卜耶伊带进南苏丹" in text(area("2011-07-01", "abyei")["rows"]), "abyei jul")
check("朱巴不是阿卜耶伊层", all(x["id"] != "abyei" for x in hit("2011-06-01", 4.859, 31.582)), "juba")

ha = area("2000-06-01", "halaib")
hat = text(ha["rows"])
check("2000 哈拉伊卜有大致虚线、不填实控", ha["probe"] is not None and "1899" in hat and "1902" in hat and "大致" in hat and "不填实控" in hat, hat[:220])
check("2000 哈拉伊卜只有声索虚线", ids_of("2000-06-01", "halaib") == ["halaib-claim"], ids_of("2000-06-01", "halaib"))
check("2000 三角区内点能点到，开罗点不到", any(x["id"] == "halaib" for x in hit("2000-06-01", 22.22, 36.63)) and all(x["id"] != "halaib" for x in hit("2000-06-01", 30.04, 31.24)), "hit")
check("1902-11-03 三角区虚线还没开始", "halaib-claim" not in ids_of("1902-11-03", "halaib"), ids_of("1902-11-03", "halaib"))

# 南苏丹：自治不等于独立
h = hit("1980-06-01", 4.859, 31.582)
c, cl = text(rows(h, "south_sudan_pre2011", "control")), text(rows(h, "south_sudan_pre2011", "claim"))
check("1980 南方自治仍属苏丹", "南方自治区" in c and "不是独立国家" in c and "苏丹" in cl, c[:180])
check("1980 喀土穆不是南苏丹层", all(x["id"] != "south_sudan_pre2011" for x in hit("1980-06-01", 15.5, 32.56)), "kht")
h = hit("1990-06-01", 4.859, 31.582)
check("1990 南方内战不填色", "不填色" in text(rows(h, "south_sudan_pre2011", "control")) and "south_sudan_pre2011-control" not in ids_of("1990-06-01", "south_sudan_pre2011"), text(rows(h, "south_sudan_pre2011", "control"))[:160])
h = hit("2011-07-08", 4.859, 31.582)
check("2011-07-08 还是南方政府", "苏丹南方政府" in text(rows(h, "south_sudan_pre2011", "control")), text(rows(h, "south_sudan_pre2011", "control"))[:120])
h = hit("2011-07-09", 4.859, 31.582)
check("2011-07-09 独立还不是会员", "还不是会员" in text(rows(h, "south_sudan_pre2011", "recognition")) and "south_sudan_pre2011-control" not in ids_of("2011-07-09", "south_sudan_pre2011"), text(rows(h, "south_sudan_pre2011", "recognition"))[:160])
h = hit("2011-07-14", 4.859, 31.582)
check("2011-07-14 写入联", "2011-07-14" in text(rows(h, "south_sudan_pre2011", "recognition")), text(rows(h, "south_sudan_pre2011", "recognition"))[:120])

# 库尔德：三省不是基尔库克，公投不是独立
h = hit("1993-06-01", 36.191, 44.009)
c = text(rows(h, "krg_core", "control"))
check("1993 三省有地区政府填色", "地区政府" in c and "krg_core-control" in ids_of("1993-06-01", "krg_core"), c[:160])
h = hit("1995-06-01", 36.191, 44.009)
check("1995 两党分裂不填色", "不填色" in text(rows(h, "krg_core", "control")) and "krg_core-control" not in ids_of("1995-06-01", "krg_core"), text(rows(h, "krg_core", "control"))[:160])
h = hit("2010-06-01", 36.191, 44.009)
c, rec = text(rows(h, "krg_core", "control")), text(rows(h, "krg_core", "recognition"))
check("2010 是联邦地区不是独立", "不是独立国家" in rec and "第 117 条" in rec and "krg_core-control" in ids_of("2010-06-01", "krg_core"), rec[:180])
check("基尔库克不在三省轮廓里", all(x["id"] != "krg_core" for x in hit("2010-06-01", 35.466, 44.392)), "kirkuk")
h = hit("2017-09-25", 36.191, 44.009)
check("2017 公投没有变成独立", "没有变成独立" in text(rows(h, "krg_core", "claim")), text(rows(h, "krg_core", "claim"))[:180])

# 也门：南北大致范围，1994 不获承认，内战不填色
h = hit("1980-06-01", 12.785, 45.018)
check("1980 亚丁是南也门", "南也门" in text(rows(h, "yemen_south", "control")) and "yemen_north" not in [x["id"] for x in h], text(rows(h, "yemen_south", "control"))[:120])
check("1980 南部有虚线无填色", "yemen_south-claim" in ids_of("1980-06-01", "yemen_south") and "yemen_south-control" not in ids_of("1980-06-01", "yemen_south"), ids_of("1980-06-01", "yemen_south"))
h = hit("1980-06-01", 15.369, 44.191)
check("1980 萨那是北也门", "阿拉伯也门共和国" in text(rows(h, "yemen_north", "control")) and "yemen_south" not in [x["id"] for x in h], text(rows(h, "yemen_north", "claim"))[:120])
h = hit("1980-06-01", 13.696, 44.731)
check("1980 达利阿不判给南北", "yemen_south" not in [x["id"] for x in h] and "yemen_north" not in [x["id"] for x in h], [x["id"] for x in h])
h = hit("1994-06-01", 12.785, 45.018)
rec = text(rows(h, "yemen_south", "recognition"))
check("1994-06 脱离没有国际承认且不填色", "没有获得国际承认" in rec and "yemen_south-control" not in ids_of("1994-06-01", "yemen_south"), rec[:160])
h = hit("1994-07-08", 12.785, 45.018)
check("1994-07-08 脱离已结束", all(r["role"] != "control" or "也门民主共和国" not in ((r.get("party") or {}).get("zh") or "") for r in next(x for x in h if x["id"] == "yemen_south")["rows"]) if any(x["id"] == "yemen_south" for x in h) else True, [x["id"] for x in h])
h = hit("2015-04-01", 15.369, 44.191)
c = text(rows(h, "yemen_war", "control"))
check("2015 内战不填色", "不填色" in c and "yemen_war-control" not in ids_of("2015-04-01", "yemen_war") and "yemen_war-claim" in ids_of("2015-04-01", "yemen_war"), c[:180])

# 加丹加：声索虚线，不填全省
h = hit("1961-06-01", -11.664, 27.479)
c, rec = text(rows(h, "katanga", "control")), text(rows(h, "katanga", "recognition"))
check("1961 加丹加不填色且没有国家承认", "不填色" in c and "没有国家正式承认" in rec and "katanga-control" not in ids_of("1961-06-01", "katanga") and "katanga-claim" in ids_of("1961-06-01", "katanga"), c[:120] + " || " + rec[:80])
check("金沙萨不是加丹加", all(x["id"] != "katanga" for x in hit("1961-06-01", -4.322, 15.313)), "kin")

# 东帝汶
h = hit("1975-12-01", -8.556, 125.56)
c = text(rows(h, "timor_leste_1975", "control"))
check("1975-12-01 宣布独立但不填成印尼", "独立革命阵线" in c and "timor_leste_1975-control" not in ids_of("1975-12-01", "timor_leste_1975"), c[:140])
h = hit("1980-06-01", -8.556, 125.56)
c, cl, rec = text(rows(h, "timor_leste_1975", "control")), text(rows(h, "timor_leste_1975", "claim")), text(rows(h, "timor_leste_1975", "recognition"))
check("1980 东帝汶是印尼占领不是承认的省", "印度尼西亚" in c and "不是印尼的合法省份" in rec and "葡萄牙" in cl, c[:80] + " || " + rec[:80])
check("1980 东帝汶有占领填色和葡萄牙虚线", "timor_leste_1975-control" in ids_of("1980-06-01", "timor_leste_1975") and "timor_leste_1975-claim" in ids_of("1980-06-01", "timor_leste_1975"), ids_of("1980-06-01", "timor_leste_1975"))
h = hit("2000-06-01", -8.556, 125.56)
c = text(rows(h, "timor_leste_1975", "control"))
check("2000 是联合国过渡行政", "过渡行政" in c and "印度尼西亚" not in c, c[:140])
h = hit("2002-05-20", -8.556, 125.56)
check("2002-05-20 独立还不是会员", "还不是" in text(rows(h, "timor_leste_1975", "recognition")) or "这期间不再填成" in text(rows(h, "timor_leste_1975", "recognition")), text(rows(h, "timor_leste_1975", "recognition"))[:160])
h = hit("2002-09-27", -8.556, 125.56)
check("2002-09-27 是联合国会员", "联合国会员" in text(rows(h, "timor_leste_1975", "recognition")), text(rows(h, "timor_leste_1975", "recognition"))[:120])

# 利比亚：虚线不是分界
h = hit("2015-06-01", 32.887, 13.191)
c, rec = text(rows(h, "libya_governments", "control")), text(rows(h, "libya_governments", "recognition"))
check("2015-06 利比亚两政府不填色", "不填色" in c and "libya_governments-control" not in ids_of("2015-06-01", "libya_governments"), c[:140])
check("2015-06 2259 还没通过", "还没有通过" in rec, rec[:160])
check("班加西同一层", any(x["id"] == "libya_governments" for x in hit("2015-06-01", 32.116, 20.068)), "ben")
h = hit("2016-06-01", 32.887, 13.191)
rec = text(rows(h, "libya_governments", "recognition"))
check("2016 2259 是政府承认不是两块主权", "2259" in rec and "不是把国土划给两个主权者" in rec, rec[:200])
check("恩贾梅纳不是利比亚层", all(x["id"] != "libya_governments" for x in hit("2016-06-01", 12.134, 15.044)), "ndj")

# 其余不画
for aid, date, needle in (
    ("lebanon_civil_war", "1983-06-01", "不画"),
    ("lebanon_civil_war", "2000-05-23", "安全带"),
    ("lebanon_civil_war", "2000-05-24", "不再记为以色列控制"),
    ("syria_civil_war", "2016-12-22", "不是阿勒颇全省"),
    ("syria_civil_war", "2019-03-23", "巴古兹"),
    ("syria_civil_war", "2024-12-08", "不是全国"),
    ("syria_civil_war", "2026-05-01", "待考"),
    ("siachen", "1990-06-01", "不画"),
    ("bd_enclaves", "2010-06-01", "111"),
    ("bd_enclaves", "2015-07-31", "还没有过户"),
    ("bd_enclaves", "2015-08-01", "不再把它们写成境外飞地"),
    ("ogaden", "1977-12-01", "不画"),
    ("ogaden", "1978-03-15", "不写成已经全部易手"),
    ("ogaden", "1978-03-24", "埃塞俄比亚"),
    ("aouzou", "1994-02-04", "不是当天已经撤军"),
    ("aouzou", "1994-05-30", "乍得控制"),
    ("hatay_1938", "1938-10-01", "不是已经并入土耳其"),
    ("hatay_1938", "1939-07-22", "不写成法国当局已经走完"),
    ("hatay_1938", "1939-07-23", "土耳其实际控制"),
):
    a = area(date, aid)
    blob = text(a["rows"])
    check(f"{date} {aid} 含「{needle}」且不画", a["probe"] is None and needle in blob and not any(i["area"] == aid for i in feats(date)), blob[:180])

check("锡亚琴不写成克什米尔全境", "不是克什米尔全境" in text(area("1990-06-01", "siachen")["rows"]), "siachen scope")
check("1990 锡亚琴实控写印度", "印度" in text(area("1990-06-01", "siachen")["rows"]) and "巴基斯坦" in text(area("1990-06-01", "siachen")["rows"]), "siachen parties")

print(f"FAILS {len(fails)}")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
