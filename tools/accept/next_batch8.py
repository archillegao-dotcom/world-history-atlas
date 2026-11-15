"""第八批：机构树上的决议、判例和专门机构。"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = os.environ.get("WHA_URL", "http://127.0.0.1:8792")
fails = []


def check(name, ok, detail=""):
    print(("OK  " if ok else "FAIL") + " " + name + ("" if ok else "  " + str(detail)))
    if not ok:
        fails.append(name)


def get(path, **params):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def org(oid, date):
    return get(f"/api/diplomacy/{oid}", date=date)


def nodes(date, oid="un"):
    return {n["zh"]: n for n in org(oid, date)["organs"]}


sc = nodes("1950-06-27")["安全理事会"]
check("1950-06-27 有第83号决议", any("第83（1950）号决议" in a["zh"] and "Korea" in a["zh"] for a in sc["acts"]), [a["zh"] for a in sc["acts"]])
check("1950-06-27 决议来源是数字图书馆", any("digitallibrary.un.org/record/112026" in (a.get("url") or "") for a in sc["acts"]), sc["acts"])

quiet = nodes("1950-06-26")["安全理事会"]
check("1950-06-26 安理会当日无记录", quiet["acts"] == [] and quiet["acts_label"] == "当日无记录", quiet["acts_label"])
check("1950-06-26 能看到更早的一条", bool(quiet.get("previous") and quiet["previous"]["date"] < "1950-06-26" and quiet["previous"]["acts"]), quiet.get("previous"))

icj = nodes("1986-06-27")["国际法院"]
check("1986-06-27 尼加拉瓜案判决", any("Nicaragua" in a["zh"] and "27 June 1986" in a["zh"] for a in icj["acts"]), [a["zh"] for a in icj["acts"]])
check("1986-06-27 案件页是 case/70", any(a.get("url") == "https://www.icj-cij.org/case/70" for a in icj["acts"]), [a.get("url") for a in icj["acts"]])

ga = nodes("1971-10-25")["大会"]
check("大会决议仅收录部分", "大会决议仅收录部分" in (ga.get("acts_note") or ""), ga.get("acts_note"))
check("1971-10-25 有第2758号决议", any("2758" in a["zh"] and "People's Republic of China" in a["zh"] for a in ga["acts"]), [a["zh"] for a in ga["acts"]])
check("2014-03-27 有第68/262号决议", any("68/262" in a["zh"] for a in nodes("2014-03-27")["大会"]["acts"]), "missing")
check("2022-10-12 有第ES-11/4号决议", any("ES-11/4" in a["zh"] for a in nodes("2022-10-12")["大会"]["acts"]), "missing")
check("1947-11-29 有第181号决议", any("181" in a["zh"] and "Palestine" in a["zh"] for a in nodes("1947-11-29")["大会"]["acts"]), "missing")
check("1950-11-03 有第377号决议", any("377" in a["zh"] and "Uniting for peace" in a["zh"] for a in nodes("1950-11-03")["大会"]["acts"]), "missing")

names = nodes("1950-06-01")
for name in ("联合国粮食及农业组织", "国际民用航空组织", "国际货币基金组织", "世界银行（国际复兴开发银行）", "万国邮政联盟", "世界卫生组织", "国际电信联盟"):
    check(f"1950 有{name}", names.get(name, {}).get("kind") == "specialized", names.get(name, {}).get("kind"))
check("1948-07-09 还没有世界卫生组织", "世界卫生组织" not in nodes("1948-07-09"), "listed")
check("1948-07-10 世界卫生组织列入", nodes("1948-07-10").get("世界卫生组织", {}).get("from") == "1948-07-10", nodes("1948-07-10").get("世界卫生组织"))
upu = nodes("1948-07-01")["万国邮政联盟"]
check("万国邮政联盟连到外交面板", upu.get("same_as") == "upu" and upu.get("same_as_zh") == "万国邮政联盟", upu.get("same_as"))
itu = nodes("1949-01-01")["国际电信联盟"]
check("国际电信联盟连到万国电报联盟", itu.get("same_as") == "itu", itu.get("same_as"))
check("1948-12-31 还没有国际电信联盟", "国际电信联盟" not in nodes("1948-12-31"), "listed")
check("国际海事组织写明日待考", "日待考" in nodes("1959-07-01")["国际海事组织"]["summary"], nodes("1959-07-01")["国际海事组织"]["summary"])
check("1959-06-30 还没有国际海事组织", "国际海事组织" not in nodes("1959-06-30"), "listed")
check("1974-12-17 有世界知识产权组织", "世界知识产权组织" in nodes("1974-12-17"), "missing")
check("2003-12-23 有世界旅游组织", "世界旅游组织" in nodes("2003-12-23"), "missing")

lotus = {n["zh"]: n for n in org("league", "1927-09-07")["organs"]}["常设国际法院"]
check("荷花号案仍在当天", any("Lotus" in a["zh"] for a in lotus["acts"]), lotus["acts"])
empty = {n["zh"]: n for n in org("league", "1927-09-06")["organs"]}["常设国际法院"]
check("1927-09-06 常设国际法院当日无记录", empty["acts_label"] == "当日无记录" and empty.get("previous", {}).get("date", "") < "1927-09-06", empty.get("previous"))

print(f"\n{len(fails)} failed" if fails else "\n0 failed")
sys.exit(1 if fails else 0)
