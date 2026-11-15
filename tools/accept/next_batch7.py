"""第七批：1912–1949 年中国省界，以及名义所属和实控派系。

用法：WHA_PORT=8792 python3 tools/accept/next_batch7.py
"""
import json, os, sys, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []

# 纬度, 经度。点位先对过简化后的省界。
CITY = {
    "北京": (39.9042, 116.4074),
    "太原": (37.8706, 112.5489),
    "昆明": (25.0389, 102.7183),
    "南宁": (22.8170, 108.3669),
    "广州": (23.1291, 113.2644),
    "南京": (32.0603, 118.7969),
    "乌鲁木齐": (43.8256, 87.6168),
    "成都": (30.5728, 104.0668),
    "银川": (38.4872, 106.2309),
    "西宁": (36.6171, 101.7782),
    "沈阳": (41.8057, 123.4315),
    "康定": (30.0500, 101.9600),
    "承德": (40.9760, 117.9360),
    "巴黎": (48.8566, 2.3522),
}


def get(path, **kw):
    q = "?" + urllib.parse.urlencode(kw) if kw else ""
    return json.load(urllib.request.urlopen(B + path + q, timeout=180))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:240])
    if not cond:
        fails.append(label)


def place(date, city):
    lat, lon = CITY[city]
    return get("/api/modules/roc_admin", date=date, lat=lat, lon=lon)["place"]


def layer(date):
    return get("/api/layers/roc_provinces", date=date)


def ids(date):
    return {row["id"] for row in layer(date)["items"]}


def geom_of(date, unit_id):
    for row in layer(date)["items"]:
        if row["id"] == unit_id:
            return row["geom"]
    return None


bj = place("1920-07-01", "北京")
check("1920-07-01 北京是直隶、北京政府、皖系",
      bj["status"] == "draw" and bj["name"] == "直隶" and bj["nominal"] == "北京政府" and bj["actual"] == "皖系",
      bj)
check("北京落点注明京兆分线没有画", "京兆" in (bj.get("line_note") or ""), bj.get("line_note"))

ty = place("1920-07-01", "太原")
check("1920-07-01 太原是山西、晋系", ty["name"] == "山西" and "晋系" in (ty["actual"] or ""), ty)
km = place("1920-07-01", "昆明")
check("1920-07-01 昆明是滇系唐继尧", "唐继尧" in (km["actual"] or ""), km)
gz = place("1920-07-01", "广州")
check("1920-07-01 广州是旧桂系驻粤", "旧桂系" in (gz["actual"] or ""), gz)
nn = place("1920-07-01", "南宁")
check("1920-07-01 南宁是旧桂系", "旧桂系" in (nn["actual"] or "") and "陆荣廷" in (nn["actual"] or ""), nn)

gz26 = place("1926-07-01", "广州")
check("1926-07-01 广州是国民政府，不是北京政府",
      gz26["nominal"] == "国民政府" and "国民政府" in (gz26["actual"] or "") and gz26["nominal"] != "北京政府", gz26)
bj26 = place("1926-07-01", "北京")
check("1926-07-01 北京实控待考，不写成奉系",
      bj26["actual"] == "实控待考" and "奉系" not in (bj26["actual"] or ""), bj26)
sy26 = place("1926-07-01", "沈阳")
check("1926-07-01 沈阳是奉系", "奉系" in (sy26["actual"] or "") and sy26["name"] == "奉天", sy26)

ty30 = place("1930-06-01", "太原")
check("1930-06-01 太原仍是晋系，名义是南京国民政府",
      "晋系" in (ty30["actual"] or "") and ty30["nominal"] == "南京国民政府", ty30)
check("1930-06-01 不把北平的另一政府写成已经成立", "9月" in (ty30.get("note") or ""), ty30.get("note"))
nj30 = place("1930-06-01", "南京")
check("1930-06-01 南京名义和实控都是南京国民政府",
      nj30["nominal"] == "南京国民政府" and nj30["actual"] == "南京国民政府", nj30)
nn30 = place("1930-06-01", "南宁")
check("1930-06-01 南宁是桂系", "桂系" in (nn30["actual"] or "") and nn30["nominal"] == "南京国民政府", nn30)
cd30 = place("1930-06-01", "成都")
check("1930-06-01 成都实控待考", cd30["actual"] == "实控待考" and cd30["name"] == "四川", cd30)

ur = place("1937-07-01", "乌鲁木齐")
check("1937-07-01 乌鲁木齐是盛世才", ur["actual"] == "盛世才" and ur["nominal"] == "南京国民政府", ur)
check("1937-07-01 太原仍是晋系", "晋系" in (place("1937-07-01", "太原")["actual"] or ""), "")
check("1937-07-01 南宁仍是桂系", "桂系" in (place("1937-07-01", "南宁")["actual"] or ""), "")
cd37 = place("1937-07-01", "成都")
check("1937-07-01 成都是刘湘，省内分界待考",
      "刘湘" in (cd37["actual"] or "") and "分界" in ((cd37.get("line_note") or "") + (cd37.get("note") or "")), cd37)
yc37 = place("1937-07-01", "银川")
check("1937-07-01 银川是马鸿逵", "马鸿逵" in (yc37["actual"] or "") and yc37["name"] == "宁夏", yc37)
xn37 = place("1937-07-01", "西宁")
check("1937-07-01 西宁是西北马家，不单写成马步芳",
      xn37["actual"] == "西北马家" and "马步芳" not in (xn37["actual"] or ""), xn37)

kd20 = place("1920-07-01", "康定")
check("1920 康定是川边特别区，不是西康省",
      kd20["name"] == "川边" and kd20["kind"] == "特别区" and kd20["name"] != "西康", kd20)
for city in ("银川", "西宁", "承德"):
    row = place("1920-07-01", city)
    check(f"1920 {city} 省界待考", row["status"] == "gap" and row["name"] is None, row)

kd30 = place("1930-06-01", "康定")
check("1930 康定尚未成立省政府", "省政府未成立" in (kd30.get("kind") or ""), kd30)
kd34 = place("1934-07-01", "康定")
check("1934-07-01 建省委员会还没成立，建制不变",
      "省政府未成立" in (kd34.get("kind") or "") and "1934-12-25" in (kd34.get("line_note") or ""), kd34)
check("1934 没有单独的西康几何", geom_of("1930-06-01", "xikang") == geom_of("1934-07-01", "xikang") and geom_of("1934-07-01", "xikang") is not None, "geom")
kd39 = place("1939-01-01", "康定")
check("1939-01-01 康定是西康省", kd39["name"] == "西康" and kd39["kind"] == "省", kd39)

check("1928-09-16 承德不画热河省", place("1928-09-16", "承德")["status"] == "gap", place("1928-09-16", "承德"))
check("1928-09-17 承德是热河省", place("1928-09-17", "承德")["name"] == "热河" and place("1928-09-17", "承德")["status"] == "draw", "")
check("1928-10-21 银川不画宁夏省", place("1928-10-21", "银川")["status"] == "gap", "")
check("1928-10-22 银川是宁夏省", place("1928-10-22", "银川")["name"] == "宁夏", "")
check("1928-06-27 北京仍叫直隶", place("1928-06-27", "北京")["name"] == "直隶", "")
check("1928-06-28 北京改称河北", place("1928-06-28", "北京")["name"] == "河北", "")
check("1929-01-27 沈阳仍叫奉天", place("1929-01-27", "沈阳")["name"] == "奉天", "")
check("1929-01-28 沈阳改称辽宁", place("1929-01-28", "沈阳")["name"] == "辽宁", "")
sy_flag = place("1928-12-29", "沈阳")
check("1928-12-29 沈阳易帜后名义是南京国民政府",
      sy_flag["nominal"] == "南京国民政府" and "张学良" in (sy_flag["actual"] or ""), sy_flag)

early = ids("1920-07-01")
check("1920 不画热河察哈尔绥远宁夏青海和缩小后的甘肃",
      not {"rehe", "chahar", "suiyuan", "ningxia", "qinghai", "gansu"} & early and "xikang" in early, sorted(early))
check("1932-06-01 不画满洲国境内的三省线", not {"fengtian", "jilin", "heilongjiang"} & ids("1932-06-01"), "")
sy47a = place("1947-05-01", "沈阳")
sy47b = place("1947-06-01", "沈阳")
check("1947-05-01 沈阳仍是旧辽宁", sy47a["status"] == "draw" and sy47a["name"] == "辽宁" and sy47a.get("scheme") == "东北三省", sy47a)
check("1947-06-01 沈阳用东北九省的辽宁", sy47b.get("scheme") == "1947东北九省" and sy47b["name"] == "辽宁", sy47b)
check("1947-06-01 辽北在图层里", "liaobei" in ids("1947-06-01"), "")
check("1945-10-24 不画台湾", "taiwan" not in ids("1945-10-24"), "")
check("1945-10-25 画出台湾", "taiwan" in ids("1945-10-25"), "")

late = place("1950-06-01", "北京")
check("1950 北京省界待考", late["status"] == "none" and late["name"] is None and "省界待考" in (late.get("note") or ""), late)
check("1950 图层没有这套省界", layer("1950-06-01")["total"] == 0, layer("1950-06-01")["total"])
paris = place("1922-06-01", "巴黎")
check("1922 巴黎省界待考", paris["status"] == "none" and "省界待考" in (paris.get("note") or "") and "不画今天的省界" in (paris.get("note") or ""), paris)

for zoom in (3, 6):
    ref = get("/api/admin1_ref", west=100, south=20, east=125, north=45, zoom=zoom)
    check(f"admin1_ref zoom {zoom} 不返回今天的省界",
          ref.get("features") == [] and "省界待考" in (ref.get("note") or "") and "不画今天的省界" in (ref.get("note") or "") and "不是历史省界" in (ref.get("note") or ""),
          ref.get("note"))

pack = layer("1922-06-01")
check("许可是 CC0", pack.get("license") == "CC0 1.0", pack.get("license"))
check("全球同类只列清单", "墨西哥" in "".join(pack.get("not_implemented") or []) and "俄国" in "".join(pack.get("not_implemented") or []) and "比利亚" not in {row["name"] for row in pack["items"]}, pack.get("not_implemented"))
check("说明写明没有使用 CHGIS", "CHGIS" in (pack.get("note") or ""), pack.get("note", "")[:180])

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
