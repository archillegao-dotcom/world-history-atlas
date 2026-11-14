"""第五批：外交面板。组织是否还在，以及几国在选定日子的资格。

用法：WHA_PORT=8792 python3 tools/accept/next_batch5.py
"""
import json, os, sys, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    q = "?" + urllib.parse.urlencode(kw) if kw else ""
    return json.load(urllib.request.urlopen(B + path + q, timeout=180))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:240])
    if not cond:
        fails.append(label)


def alive(date):
    return {o["id"]: o for o in get("/api/diplomacy", date=date)["orgs"]}


def org(oid, date):
    return get(f"/api/diplomacy/{oid}", date=date)


def st(rec, name):
    for m in rec["members"]:
        if m["name"] == name or name in (m["name"] or ""):
            return m["status"]
    return None


def row(rec, name):
    for m in rec["members"]:
        if name in (m["name"] or ""):
            return m
    return None


ids = set(alive("1920-01-10"))
check("1920-01-10 有国际联盟", "league" in ids, sorted(ids))
check("1920-01-10 还没有联合国", "un" not in ids, sorted(ids))

g1925 = org("league", "1925-06-01")
check("1925 联盟还在", g1925["alive"] and g1925["view_status"] == "存续", g1925["view_status"])
check("1925 德国尚未加入", st(g1925, "德意志国") == "尚未加入", st(g1925, "德意志国"))
check("1925 日本是成员国", st(g1925, "大日本帝国") == "成员国", st(g1925, "大日本帝国"))
check("1925 苏联尚未加入", st(g1925, "苏联") == "尚未加入", st(g1925, "苏联"))
check("1925 英国用当时国号", st(g1925, "大不列颠及爱尔兰联合王国") == "成员国", [m["name"] for m in g1925["members"]])

g1927 = org("league", "1927-06-01")
check("1927 德国是成员国", st(g1927, "德意志国") == "成员国", st(g1927, "德意志国"))
check("1927 日本仍是成员国", st(g1927, "大日本帝国") == "成员国", st(g1927, "大日本帝国"))

g1935 = org("league", "1935-06-01")
check("1935 联盟还在", g1935["alive"], g1935["view_status"])
check("1935 德国已宣布退出", st(g1935, "德意志国") == "已宣布退出，通知期未满", st(g1935, "德意志国"))
check("1935 日本已经退出", st(g1935, "大日本帝国") == "已退出", st(g1935, "大日本帝国"))
check("1935 苏联是成员国", st(g1935, "苏联") == "成员国", st(g1935, "苏联"))
check("1935 国联名册已写全", g1935["incomplete"] is False and "名单不完整" not in (g1935.get("list_note") or ""), g1935["active_count"])
check("1935 会员名不是联邦德国", all(m["name"] != "联邦德国" and m["name"] != "德国" for m in g1935["members"]), [m["name"] for m in g1935["members"]])

g1940 = org("league", "1940-06-01")
check("1940 联盟还在", g1940["alive"], True)
check("1940 苏联被开除", st(g1940, "苏联") == "被开除", st(g1940, "苏联"))
check("1940 德国已退出", st(g1940, "德意志国") == "已退出", st(g1940, "德意志国"))
check("1940 日本已退出", st(g1940, "大日本帝国") == "已退出", st(g1940, "大日本帝国"))

may = alive("1946-05-01")
check("1946-05 联盟已经停止", "league" not in may, sorted(may))
check("1946-05 联合国还在", "un" in may and may["un"]["view_status"] == "存续", may.get("un"))

u1950 = org("un", "1950-06-01")
check("1950 联合国还在", u1950["alive"], u1950["view_status"])
check("1950 中国席位是中华民国", st(u1950, "中华民国") == "中国席位", [(m["name"], m["status"]) for m in u1950["members"]])
check("1950 不另列中华人民共和国", st(u1950, "中华人民共和国") is None, st(u1950, "中华人民共和国"))
check("1950 苏联是成员国", st(u1950, "苏联") == "成员国", st(u1950, "苏联"))
check("1950 日本尚未到接纳日", st(u1950, "日本") == "尚未加入", st(u1950, "日本"))

u1972 = org("un", "1972-06-01")
check("1972 中国席位是中华人民共和国", st(u1972, "中华人民共和国") == "中国席位", st(u1972, "中华人民共和国"))
roc = row(u1972, "中华民国")
check("1972 中华民国不再持有席位", roc and roc["status"] == "不再持有这一席位", roc)
check("1972 联邦德国尚未到接纳日", st(u1972, "德意志联邦共和国") == "尚未加入", st(u1972, "德意志联邦共和国"))
check("1972 联合国名册已写全", u1972["incomplete"] is False, u1972["active_count"])

itu = org("itu", "1865-05-17")
names = [m["name"] for m in itu["members"]]
check("1865 电报联盟有普鲁士", "普鲁士王国" in names, names)
check("1865 电报联盟不把德国写成签署方", "德国" not in names and "德意志国" not in names, names)
check("1865 电报联盟签署方后来会籍未核", all(m["status"] == "签署方，后来的会籍未核" for m in itu["members"]), itu["members"][0]["status"])

upu_sign = org("upu", "1874-10-09")
upu_on = org("upu", "1875-07-01")
check("1874-10-09 邮政联盟尚未生效", upu_sign["view_status"] == "已签署，尚未生效", upu_sign["view_status"])
check("1875-07-01 邮政联盟生效", upu_on["view_status"] == "存续", upu_on["view_status"])
check("邮政联盟写奥匈帝国", any("奥匈" in m["name"] for m in upu_sign["members"]), [m["name"] for m in upu_sign["members"]])

pca_sign = org("pca", "1899-07-29")
pca_on = org("pca", "1900-09-04")
check("1899 仲裁法院尚未生效", pca_sign["view_status"] == "已签署，尚未生效" and pca_sign["members"] == [], pca_sign["view_status"])
check("1900-09-04 仲裁法院存续且名单不完整", pca_on["view_status"] == "存续" and pca_on["incomplete"], pca_on["list_note"][:40])

early = org("concert", "1816-06-01")
later = org("concert", "1819-06-01")
check("1816 会议体系还没有法国", st(early, "波旁复辟") == "尚未加入", [m["name"] for m in early["members"]])
check("1819 法国已进入会商", st(later, "波旁复辟") == "会商国", st(later, "波旁复辟"))
check("1823 会议体系不再列出", "concert" not in alive("1823-01-01"), "ok")
check("会议体系类型是非正式", early["type_zh"] == "非正式会议体系", early["type_zh"])

loc = get("/api/locate", date="1935-06-01", lat="51.51", lon="-0.13")
panel = get("/api/modules/diplomacy", date="1935-06-01", snap=loc["snapshot"], fid=loc["polity"]["fid"])
quals = {it["zh"]: it.get("qualification") for it in panel["items"]}
check("1935 伦敦面板写明联盟资格", quals.get("国际联盟") == "成员国", quals)

print(f"\n{len(fails)} failed" if fails else "\n0 failed")
sys.exit(1 if fails else 0)
