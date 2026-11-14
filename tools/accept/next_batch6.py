"""第六批：联合国与国际联盟的完整名册，以及机构树骨架。

用法：WHA_PORT=8792 python3 tools/accept/next_batch6.py
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


def org(oid, date):
    return get(f"/api/diplomacy/{oid}", date=date)


_RANK = {
    "成员国": 0, "中国席位": 0, "已宣布退出，通知期未满": 1,
    "不自动延续原会籍，不得参加大会工作": 2, "加入日待考": 3,
    "已退出": 4, "已并入另一会员": 4, "已从名册除去": 4,
    "尚未加入": 5,
}


def _hits(rec, name, exact=False):
    hits = []
    for m in rec["members"]:
        label = m["name"] or ""
        if label == name or (not exact and name in label):
            hits.append(m)
    hits.sort(key=lambda m: _RANK.get(m["status"], 9))
    return hits


def st(rec, name, exact=False):
    hits = _hits(rec, name, exact)
    return hits[0]["status"] if hits else None


def nm(rec, name, exact=False):
    hits = _hits(rec, name, exact)
    return hits[0]["name"] if hits else None


# 增长页的年末人数。10月24日当天不到51，是因为事实表按各国交存日，不把51国都写成同一天。
YEAR = {
    "1945-12-31": 51, "1946-12-31": 55, "1947-12-31": 57, "1948-12-31": 58,
    "1949-12-31": 59, "1950-12-31": 60, "1955-12-31": 76, "1956-12-31": 80,
    "1957-12-31": 82, "1958-12-31": 82, "1960-12-31": 99, "1961-12-31": 104,
    "1962-12-31": 110, "1963-12-31": 113, "1964-12-31": 115, "1965-12-31": 117,
    "1966-12-31": 122, "1967-12-31": 123, "1968-12-31": 126, "1971-12-31": 132,
    "1973-12-31": 135, "1990-12-31": 159, "1991-12-31": 166, "1992-12-31": 179,
    "1993-12-31": 184, "1999-12-31": 188, "2000-12-31": 189, "2002-12-31": 191,
    "2006-12-31": 192, "2011-12-31": 193, "2020-06-01": 193,
}
for day, n in YEAR.items():
    rec = org("un", day)
    check(f"联合国 {day} 在册 {n}", rec["active_count"] == n and rec["incomplete"] is False, rec["active_count"])

opening = org("un", "1945-10-24")
check("1945-10-24 不到51国", opening["active_count"] < 51, opening["active_count"])
check("1945-10-24 澳大利亚还没交存", st(opening, "澳大利亚") == "尚未加入", st(opening, "澳大利亚"))
nov = org("un", "1945-11-01")
check("1945-11-01 澳大利亚已加入", st(nov, "澳大利亚") == "成员国", st(nov, "澳大利亚"))

u1958 = org("un", "1958-06-01")
check("1958 叙利亚已并入", st(u1958, "叙利亚") == "已并入另一会员", st(u1958, "叙利亚"))
check("1958 埃及称阿拉伯联合共和国", nm(u1958, "阿拉伯联合共和国") == "阿拉伯联合共和国", nm(u1958, "阿拉伯联合共和国"))
u1961 = org("un", "1961-10-13")
check("1961-10-13 叙利亚恢复会籍", st(u1961, "叙利亚") == "成员国", st(u1961, "叙利亚"))

check("1965 印尼已退出", st(org("un", "1965-06-01"), "印度尼西亚") == "已退出", st(org("un", "1965-06-01"), "印度尼西亚"))
check("1966-09-27 印尼尚未恢复", st(org("un", "1966-09-27"), "印度尼西亚") == "已退出", st(org("un", "1966-09-27"), "印度尼西亚"))
check("1966-09-28 印尼恢复", st(org("un", "1966-09-28"), "印度尼西亚") == "成员国", st(org("un", "1966-09-28"), "印度尼西亚"))

u1964 = org("un", "1964-06-01")
check("1964 坦噶尼喀已改联合共和国", "坦噶尼喀和桑给巴尔" in (nm(u1964, "坦噶尼喀和桑给巴尔") or ""), nm(u1964, "坦"))
check("1964 桑给巴尔已并入", st(u1964, "桑给巴尔", exact=True) == "已并入另一会员", st(u1964, "桑给巴尔", exact=True))

u1990 = org("un", "1990-10-03")
check("1990-10-03 民主德国已并入", st(u1990, "德意志民主共和国") == "已并入另一会员", st(u1990, "德意志民主共和国"))
check("1990-10-03 联邦德国仍是会员", st(u1990, "德意志联邦共和国") == "成员国", st(u1990, "德意志联邦共和国"))
check("1990-06-01 也门已经合并", nm(org("un", "1990-06-01"), "也门共和国") == "也门共和国", nm(org("un", "1990-06-01"), "也门"))

u1991 = org("un", "1991-12-24")
check("1991-12-24 俄罗斯联邦继续苏联席位", nm(u1991, "俄罗斯联邦") == "俄罗斯联邦" and st(u1991, "俄罗斯联邦") == "成员国", (nm(u1991, "俄罗斯"), st(u1991, "俄罗斯")))
check("1991-12-23 仍称苏联", nm(org("un", "1991-12-23"), "苏联") == "苏联", nm(org("un", "1991-12-23"), "苏联"))

u1992 = org("un", "1992-09-22")
check("1992-09-22 南斯拉夫不自动延续", st(u1992, "南斯拉夫", exact=True) == "不自动延续原会籍，不得参加大会工作", st(u1992, "南斯拉夫", exact=True))
u2000 = org("un", "2000-11-01")
check("2000-11-01 旧南斯拉夫从名册除去", st(u2000, "南斯拉夫", exact=True) == "已从名册除去", st(u2000, "南斯拉夫", exact=True))
check("2000-11-01 南斯拉夫联盟共和国是新会员", nm(u2000, "南斯拉夫联盟共和国") == "南斯拉夫联盟共和国" and st(u2000, "南斯拉夫联盟共和国") == "成员国", nm(u2000, "南斯拉夫联盟"))

check("1956-12-17 日本尚未加入", st(org("un", "1956-12-17"), "日本") == "尚未加入", st(org("un", "1956-12-17"), "日本"))
check("1956-12-18 日本加入", st(org("un", "1956-12-18"), "日本") == "成员国", st(org("un", "1956-12-18"), "日本"))

tree = org("un", "1950-06-01")
organs = {n["zh"]: n for n in tree["organs"]}
for name in ("大会", "安全理事会", "经济及社会理事会", "托管理事会", "国际法院", "秘书处"):
    check(f"1950 有{name}", name in organs and organs[name]["kind"] == "principal", organs.get(name, {}).get("kind"))
check("1950 教科文组织是专门机构", organs.get("联合国教育、科学及文化组织", {}).get("kind") == "specialized", organs.get("联合国教育、科学及文化组织"))
check("1950 国际法院当日无记录", organs["国际法院"]["acts"] == [] and organs["国际法院"]["acts_label"] == "当日无记录", organs["国际法院"]["acts_label"])
check("1994-11-01 托管理事会停止运作", "托管理事会" not in {n["zh"] for n in org("un", "1994-11-01")["organs"]}, "ok")
icj = {n["zh"]: n for n in org("un", "1949-04-09")["organs"]}["国际法院"]
check("1949-04-09 科孚海峡案", any("Corfu" in a["zh"] for a in icj["acts"]), [a["zh"] for a in icj["acts"]])

league = org("league", "1946-04-18")
check("1946-04-18 国联仍有44国", league["active_count"] == 44 and league["record_count"] == 63, (league["active_count"], league["record_count"]))
check("国联名册已写全", league["incomplete"] is False, league["incomplete"])
check("1920-07-01 中国尚未加入国联", st(org("league", "1920-07-01"), "中华民国") == "尚未加入", st(org("league", "1920-07-01"), "中华民国"))
check("1920-07-16 中国是国联会员", st(org("league", "1920-07-16"), "中华民国") == "成员国", st(org("league", "1920-07-16"), "中华民国"))
check("1927 西班牙仍是会员", st(org("league", "1927-06-01"), "西班牙") == "成员国", st(org("league", "1927-06-01"), "西班牙"))
check("1926-06-12 巴西已宣布退出", st(org("league", "1926-06-12"), "巴西") == "已宣布退出，通知期未满", st(org("league", "1926-06-12"), "巴西"))
check("1928-06-13 巴西已经退出", st(org("league", "1928-06-13"), "巴西") == "已退出", st(org("league", "1928-06-13"), "巴西"))
check("1937-12-11 意大利已宣布退出", st(org("league", "1937-12-11"), "意大利王国") == "已宣布退出，通知期未满", st(org("league", "1937-12-11"), "意大利"))
check("1939-12-10 意大利已经退出", st(org("league", "1939-12-10"), "意大利王国") == "已退出", st(org("league", "1939-12-10"), "意大利"))
check("1920 罗马尼亚加入日待考", st(org("league", "1920-06-01"), "罗马尼亚") == "加入日待考", st(org("league", "1920-06-01"), "罗马尼亚"))
check("1921 罗马尼亚是会员", st(org("league", "1921-06-01"), "罗马尼亚") == "成员国", st(org("league", "1921-06-01"), "罗马尼亚"))

lt = {n["zh"]: n for n in org("league", "1927-09-07")["organs"]}
for name in ("大会", "行政院", "秘书处", "常设国际法院", "国际劳工组织"):
    check(f"1927 有{name}", name in lt, sorted(lt))
check("1927-09-07 荷花号案", any("Lotus" in a["zh"] for a in lt["常设国际法院"]["acts"]), lt["常设国际法院"]["acts"])
check("1927 劳工组织不是主要机关", lt["国际劳工组织"]["kind"] == "related", lt["国际劳工组织"]["kind"])
check("1922-02-14 还没有常设国际法院", "常设国际法院" not in {n["zh"] for n in org("league", "1922-02-14")["organs"]}, "ok")
check("常设仲裁法院仍是名单不完整", org("pca", "1950-06-01")["incomplete"] is True, org("pca", "1950-06-01")["incomplete"])

print(f"\n{len(fails)} failed" if fails else "\n0 failed")
sys.exit(1 if fails else 0)
