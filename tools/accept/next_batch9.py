"""第九批：五个国家的宪法时间线。对运行中的 8792 做前后一日查询。"""
import json, sys, urllib.parse, urllib.request
B = "http://127.0.0.1:8792"
fails = []

def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=120))

def law(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    if not p:
        return None, None
    body = get("/api/modules/constitution", date=date, snap=loc["snapshot"], fid=p["fid"])
    return p, body

def names(body):
    out = []
    for it in body.get("items") or []:
        out.append(it.get("title") or "")
        out.append(it.get("kind_zh") or "")
    return out

def check(why, date, lat, lon, present=(), absent=(), note_has=None):
    p, body = law(date, lat, lon)
    if body is None:
        fails.append(why + " 没有点到多边形")
        return
    blob = " ".join(names(body))
    note = (body.get("note") or "") + (body.get("coverage") or "")
    bad = []
    for t in present:
        if t not in blob:
            bad.append("缺少 " + t)
    for t in absent:
        if t in blob:
            bad.append("不该出现 " + t)
    if note_has and note_has not in note:
        bad.append("说明里没有「" + note_has + "」")
    if bad:
        fails.append(why + " " + "；".join(bad))
    print(("?? " if bad else "OK ") + why)

NY, MS, TU, RM, MD, BJ, TP = (40.71, -74.01), (55.75, 37.62), (45.07, 7.69), (41.90, 12.50), (40.42, -3.70), (39.90, 116.40), (25.03, 121.57)

check("1788-06-21 纽约仍是邦联条例", "1788-06-21", *NY, present=["1777年邦联条例"], absent=["1787年美国宪法"])
check("1789-03-03 纽约仍是邦联条例", "1789-03-03", *NY, present=["1777年邦联条例"], absent=["1787年美国宪法"])
check("1789-03-04 纽约是美国宪法", "1789-03-04", *NY, present=["1787年美国宪法", "正式宪法"], absent=["1777年邦联条例"])

check("1918-07-09 莫斯科还没有1918年宪法", "1918-07-09", *MS, absent=["1918年俄罗斯社会主义联邦苏维埃共和国宪法"])
check("1918-07-10 莫斯科是1918年宪法", "1918-07-10", *MS, present=["1918年俄罗斯社会主义联邦苏维埃共和国宪法"], absent=["1924年苏联宪法"])
check("1922-12-29 莫斯科仍是1918年宪法", "1922-12-29", *MS, present=["1918年俄罗斯社会主义联邦苏维埃共和国宪法"])
check("1922-12-30 莫斯科还没有1924年宪法", "1922-12-30", *MS, absent=["1924年苏联宪法", "1918年俄罗斯社会主义联邦苏维埃共和国宪法"], note_has="1924年1月31日")
check("1924-01-31 莫斯科是1924年宪法", "1924-01-31", *MS, present=["1924年苏联宪法"], absent=["1936年苏联宪法"])
check("1936-12-04 莫斯科仍是1924年宪法", "1936-12-04", *MS, present=["1924年苏联宪法"], absent=["1936年苏联宪法"])
check("1936-12-05 莫斯科是1936年宪法", "1936-12-05", *MS, present=["1936年苏联宪法"], absent=["1924年苏联宪法"])
check("1977-10-06 莫斯科仍是1936年宪法", "1977-10-06", *MS, present=["1936年苏联宪法"], absent=["1977年苏联宪法"])
check("1977-10-07 莫斯科是1977年宪法", "1977-10-07", *MS, present=["1977年苏联宪法"], absent=["1936年苏联宪法"])
check("1991-12-25 莫斯科仍是1977年宪法", "1991-12-25", *MS, present=["1977年苏联宪法"], absent=["1993年俄罗斯联邦宪法"])
check("1991-12-26 莫斯科还没有1993年宪法", "1991-12-26", *MS, absent=["1977年苏联宪法", "1993年俄罗斯联邦宪法"], note_has="1978年")
check("1993-12-24 莫斯科还没有1993年宪法", "1993-12-24", *MS, absent=["1993年俄罗斯联邦宪法"])
check("1993-12-25 莫斯科是1993年宪法", "1993-12-25", *MS, present=["1993年俄罗斯联邦宪法", "正式宪法"])

check("1848-03-04 都灵还没有列入宪章", "1848-03-04", *TU, absent=["阿尔贝蒂诺宪章"])
check("1848-05-08 都灵是阿尔贝蒂诺宪章", "1848-05-08", *TU, present=["阿尔贝蒂诺宪章", "宪章"])
check("1946-06-01 罗马仍是宪章", "1946-06-01", *RM, present=["阿尔贝蒂诺宪章"], absent=["1948年意大利共和国宪法"])
check("1947-12-27 罗马仍是宪章", "1947-12-27", *RM, present=["阿尔贝蒂诺宪章"], absent=["1948年意大利共和国宪法"])
check("1948-01-01 罗马是共和国宪法", "1948-01-01", *RM, present=["1948年意大利共和国宪法", "正式宪法"], absent=["阿尔贝蒂诺宪章"])

check("1931-12-08 马德里还没有1931年宪法", "1931-12-08", *MD, absent=["1931年西班牙宪法"])
check("1931-12-09 马德里是1931年宪法", "1931-12-09", *MD, present=["1931年西班牙宪法", "正式宪法"], absent=["劳动宪章"])
check("1939-03-31 马德里仍是1931年宪法", "1939-03-31", *MD, present=["1931年西班牙宪法"], absent=["劳动宪章"])
check("1939-04-01 马德里是基本法不是正式宪法", "1939-04-01", *MD, present=["劳动宪章", "基本法"], absent=["1931年西班牙宪法", "1978年西班牙宪法", "正式宪法"])
check("1942-07-18 马德里还没有议会组织法", "1942-07-18", *MD, present=["劳动宪章"], absent=["议会组织法"])
check("1942-07-19 马德里有议会组织法", "1942-07-19", *MD, present=["议会组织法", "基本法"])
check("1978-12-28 马德里仍是基本法", "1978-12-28", *MD, present=["劳动宪章", "基本法"], absent=["1978年西班牙宪法"])
check("1978-12-29 马德里是1978年宪法", "1978-12-29", *MD, present=["1978年西班牙宪法", "正式宪法"], absent=["劳动宪章", "政治改革法", "基本法"])

check("1949-09-29 北京不套共同纲领", "1949-09-29", *BJ, absent=["1949年共同纲领", "1954年9月20日宪法"])
check("1949-10-01 北京是共同纲领", "1949-10-01", *BJ, present=["1949年共同纲领", "临时宪法/约法"], absent=["1954年9月20日宪法"])
check("1954-09-19 北京仍是共同纲领", "1954-09-19", *BJ, present=["1949年共同纲领"], absent=["1954年9月20日宪法"])
check("1954-09-20 北京是1954年宪法", "1954-09-20", *BJ, present=["1954年9月20日宪法"], absent=["1949年共同纲领"])
check("1975-01-16 北京仍是1954年宪法", "1975-01-16", *BJ, present=["1954年9月20日宪法"], absent=["1975年1月17日宪法"])
check("1975-01-17 北京是1975年宪法", "1975-01-17", *BJ, present=["1975年1月17日宪法"], absent=["1954年9月20日宪法"])
check("1978-03-04 北京仍是1975年宪法", "1978-03-04", *BJ, present=["1975年1月17日宪法"], absent=["1978年3月5日宪法"])
check("1978-03-05 北京是1978年宪法", "1978-03-05", *BJ, present=["1978年3月5日宪法"], absent=["1975年1月17日宪法"])
check("1982-12-03 北京仍是1978年宪法", "1982-12-03", *BJ, present=["1978年3月5日宪法"], absent=["1982年12月4日宪法"])
check("1982-12-04 北京是1982年宪法", "1982-12-04", *BJ, present=["1982年12月4日宪法"], absent=["1978年3月5日宪法"])
check("2000-06-01 台北不套中华人民共和国宪法", "2000-06-01", *TP, absent=["1982年12月4日宪法", "1949年共同纲领"], note_has="没有收录")

print(f"FAIL {len(fails)}")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
