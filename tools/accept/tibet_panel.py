#!/usr/bin/env python3
"""甘丹颇章面板，以及藏南、阿克赛钦样本点。服务需已在 8792。"""
import json
import os
import sys
import urllib.request

BASE = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
FAIL = 0


def get(url):
    with urllib.request.urlopen(BASE + url, timeout=60) as r:
        return json.load(r)


def blob(date, lon, lat):
    loc = get(f"/api/locate?date={date}&lon={lon}&lat={lat}")
    p = loc.get("polity") or {}
    fid, snap = p.get("fid"), loc.get("snapshot")
    q = f"&lat={lat}&lon={lon}"
    regime = get(f"/api/modules/regime?date={date}&snap={snap}&fid={fid}{q}") if fid else {}
    leaders = get(f"/api/modules/leaders?date={date}&snap={snap}&fid={fid}{q}") if fid else {}
    text = json.dumps({"p": p, "r": regime, "l": leaders}, ensure_ascii=False)
    return p, regime, leaders, text


def check(label, date, lon, lat, say=(), unsay=(), name=None, cat=None, prec=None):
    global FAIL
    p, regime, leaders, text = blob(date, lon, lat)
    bad = []
    if name and (regime.get("state") or {}).get("name") != name and p.get("NAME_ZH") != name and p.get("NAME") != name:
        # 名称可能在政权面板，也可能在多边形中文名
        shown = (regime.get("state") or {}).get("name") or p.get("NAME_ZH") or p.get("NAME")
        if name not in (shown or ""):
            bad.append(f"name {shown}")
    if cat and p.get("TERR_CAT") != cat:
        bad.append(f"cat {p.get('TERR_CAT')}")
    if prec is not None and p.get("BORDERPRECISION") != prec:
        bad.append(f"prec {p.get('BORDERPRECISION')}")
    for s in say:
        if s not in text:
            bad.append("missing " + s)
    for s in unsay:
        if s in text:
            bad.append("unexpected " + s)
    if bad:
        FAIL += 1
        print("FAIL", label, "; ".join(bad))
    else:
        print("PASS", label)


LH, TW, AK = (91.117, 29.65), (91.86, 27.59), (79.0, 35.2)
CD = (97.17, 31.14)

check("1912拉萨仍是中华民国", "1912-06-01", *LH, say=("中华民国", "已知缺陷", "不是已经核实", "不是史实确证"), unsay=("热振活佛", "十三世达赖"))
check("1913拉萨是甘丹颇章", "1913-02-01", *LH, name="甘丹颇章", prec=1, say=("十三世达赖喇嘛土登嘉措", "启用日待考"), unsay=("毛泽东", "绝对专制", "Flag"))
check("去世当日仍列十三世", "1933-12-17", *LH, say=("土登嘉措",))
check("去世次日未记录在任者", "1933-12-18", *LH, say=("未记录", "1934年1月"), unsay=("土登嘉措"))
check("1934年6月是热振", "1934-06-01", *LH, say=("热振活佛",), unsay=("达扎活佛", "毛泽东"))
check("1941年摄政交接月份待考", "1941-06-01", *LH, say=("热振活佛", "达扎活佛", "月份待考", "不是两人共治", "不写成与热振共治"), unsay=("全年",))
check("1944年达扎掌政，十四世尚未亲政", "1944-12-01", *LH, prec=1, say=("达扎活佛", "尚未亲政", "摄政"), unsay=("热振活佛", "毛泽东", "中华人民共和国主席", "全年"))
check("亲政前一日仍是达扎", "1950-11-16", *LH, say=("达扎活佛", "尚未亲政"), unsay=("达赖喇嘛（亲政）",))
check("1950-11-17亲政", "1950-11-17", *LH, say=("亲政", "丹增嘉措"), unsay=("达扎活佛",))
check("1950-10-01拉萨仍单列", "1950-10-01", *LH, name="甘丹颇章", unsay=("毛泽东", "昌都大致框"))
check("1950-10-05拉萨没有整块易手", "1950-10-05", *LH, name="甘丹颇章", prec=1, say=("不是新测的控制线",), unsay=("毛泽东",))
check("昌都10月23日还没有整框易手", "1950-10-23", *CD, name="甘丹颇章", unsay=("不是辖境",))
check("昌都10月24日是大致框", "1950-10-24", *CD, say=("昌都大致框", "不是辖境", "大致"), unsay=("十三世达赖", "达扎活佛"))
check("同一天拉萨仍是甘丹颇章", "1950-10-24", *LH, name="甘丹颇章", unsay=("不是辖境",))
check("协议日拉萨不变色", "1951-05-23", *LH, name="甘丹颇章", say=("不是1950年10月2日或1951年5月23日",), unsay=("毛泽东",))
check("进驻噶大克前一日", "1951-08-08", *LH, name="甘丹颇章")
check("8月9日起标成数据不足", "1951-08-09", *LH, name="数据不足（旧轮廓，不是实控重建）", cat="unverified", prec=1,
      say=("数据不足", "不是无人统治", "不是中华人民共和国的实控色", "10月26日"), unsay=("毛泽东",))
check("拉萨主力进驻日仍不是全区变色", "1951-10-26", *LH, cat="unverified", say=("10月26日", "都不是全区变色"))
check("命令前一日仍未核实", "1959-03-27", *LH, cat="unverified")
check("3月28日回到中国多边形", "1959-03-28", *LH, say=("自即日起", "中华人民共和国", "不是该日全境战线"), unsay=("范围未核实",))
check("1800年达旺不套今天的实控", "1800-01-01", *TW, unsay=("印度实控", "中国声索线南", "达旺样本"))
check("1944年达旺不按今天的印度实控", "1944-12-01", *TW, say=("不按今天的印度实控", "中国声索"), unsay=("有效管治已经建立",))
check("1951年2月5日仍不写成已管治", "1951-02-05", *TW, say=("1951年2月6日以前",))
check("1951年2月6日人员进入", "1951-02-06", *TW, say=("印度人员进入", "不写成整个达旺已经有效管治"))
check("1951年8月达旺写到管治建立", "1951-08-15", *TW, say=("1951年8月", "不是8月1日整个藏南", "中国声索"))
check("2000年达旺仍是声索不是实控改涂", "2000-06-01", *TW, say=("实际控制看底图颜色", "中国声索", "不是实际边界"))
check("1800年阿克赛钦不套后来的争议", "1800-01-01", *AK, unsay=("印度声索", "公路"))
check("1944年阿克赛钦不写成中国实控", "1944-12-01", *AK, say=("不回写", "也不写成中国实控"), unsay=("底图颜色是中国多边形",))
check("1947年8月15日的变色不是当天核实", "1947-08-15", *AK, say=("不是当天核实的易手", "印度声索"))
check("1957年8月31日还不是公路月", "1957-08-31", *AK, say=("不是1957年9月的公路",))
check("1957年9月只是公路陈述的月份", "1957-09-01", *AK, say=("不是9月1日整块阿克赛钦易手", "印度声索"))

def total(label, date, lon, lat, n):
    global FAIL
    _, _, leaders, _ = blob(date, lon, lat)
    got = leaders.get("total")
    names = [x.get("name") for x in leaders.get("curated_offices") or []]
    if got != n:
        FAIL += 1
        print("FAIL", label, got, names)
    else:
        print("PASS", label, got)


total("1941年名单三人", "1941-06-01", *LH, 3)
total("1944年名单两人", "1944-12-01", *LH, 2)
total("1934年只有热振计入", "1934-06-01", *LH, 1)

print("FAIL", FAIL)
sys.exit(1 if FAIL else 0)
