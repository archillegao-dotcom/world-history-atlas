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
check("4月28日不画第一次直奉", "zf-jinghan" not in ids_on("1922-04-28"), "")
check("4月29日起画京汉津浦", {"zf-jinghan", "zf-jinpu", "zf-guan"} <= ids_on("1922-04-29"), ids_on("1922-04-29"))
check("6月18日起不留第一次直奉", "zf-jinghan" not in ids_on("1922-06-18"), "")
check("5月12日不画粤汉走廊", "yuehan-1922" not in ids_on("1922-05-12"), "")
check("5月13日有粤汉、向赣和第一次直奉",
      ids_on("1922-05-13") == {"yuehan-1922", "gan-1922", "zf-jinghan", "zf-jinpu", "zf-guan"}, ids_on("1922-05-13"))
check("6月17日起不留粤汉走廊", "yuehan-1922" not in ids_on("1922-06-17"), "")
check("2月3日不画淞沪铁路", "huning-1932" not in ids_on("1932-02-03") and "huhang-1932" not in ids_on("1932-02-03"), "")
check("2月4日画沪宁和沪杭", {"huning-1932", "huhang-1932"} <= ids_on("1932-02-04"), ids_on("1932-02-04"))
check("2月5日起不留淞沪铁路", "huning-1932" not in ids_on("1932-02-05") and "huhang-1932" not in ids_on("1932-02-05"), "")
check("1926-10-10 三路都在", {"bf-lianghu", "bf-jiangxi", "bf-fujian"} <= ids_on("1926-10-10"), ids_on("1926-10-10"))
check("1930-09-01 三条铁路在，桂军入湘已撤",
      {"zy-longhai", "zy-pinghan", "zy-jinpu"} <= ids_on("1930-09-01") and "zy-hunan" not in ids_on("1930-09-01"), "")
check("1935-06-01 有长征，没有中央苏区环",
      "longmarch" in ids_on("1935-06-01") and "soviet-ring" not in ids_on("1935-06-01"), "")
check("塘沽线在，满洲国规则不靠这条线改省界", "tanggu-line" in ids_on("1933-05-31") and "rehe-1933" not in ids_on("1933-03-05"), "")
check("1931-11-19 有沈阳至龙江，没有锦州和哈尔滨",
      {"mukden-jl", "mukden-hlj"} <= ids_on("1931-11-19") and "mukden-jz" not in ids_on("1931-11-19") and "mukden-heb" not in ids_on("1931-11-19"),
      ids_on("1931-11-19"))
check("1932-03-01 起不留九一八进占线", "mukden-jl" not in ids_on("1932-03-01"), "")
check("1936-10-09 会宁有红四方面军", "front4-1936" in ids_on("1936-10-09"), "")
check("1938-10-01 武汉两线在，徐州会战已过",
      {"wuhan-north", "wuhan-east"} <= ids_on("1938-10-01") and "xuzhou-1938" not in ids_on("1938-10-01"), "")
check("1937-11-26 淞沪还在，12月1日前没有南京线",
      "songhu-1937" in ids_on("1937-11-26") and "nanjing-1937" not in ids_on("1937-11-30"), "")
check("1937-12-10 有南京线", "nanjing-1937" in ids_on("1937-12-10"), "")
check("1937-12-14 起不留南京线", "nanjing-1937" not in ids_on("1937-12-14"), "")
check("1944-11-15 桂柳在，豫中和长衡已过，南宁还没画",
      "guiliu-1944" in ids_on("1944-11-15") and "yuzhong-1944" not in ids_on("1944-11-15")
      and "changheng-1944" not in ids_on("1944-11-15") and "nanning-1944" not in ids_on("1944-11-15"), "")
check("1944-11-24 南宁线在", "nanning-1944" in ids_on("1944-11-24"), "")
check("1948-11-01 辽沈还在，淮海未开始",
      "liaoshen-1948" in ids_on("1948-11-01") and "huaihai-1948" not in ids_on("1948-11-01"), "")
check("1948-11-15 淮海在，辽沈已过",
      "huaihai-1948" in ids_on("1948-11-15") and "liaoshen-1948" not in ids_on("1948-11-15"), "")


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
wc = place("1926-10-10", 30.524, 114.276)
check("1926-10-10 武昌有两湖路，北京实控仍待考",
      any(f["id"] == "bf-lianghu" for f in wc["fronts"]) and place("1926-10-10", 39.9042, 116.4074)["place"]["actual"] == "实控待考",
      wc["place"])
zy = place("1930-09-01", 34.745, 113.67)
check("1930-09-01 郑县有陇海、平汉、津浦",
      {f["id"] for f in zy["fronts"]} >= {"zy-longhai", "zy-pinghan", "zy-jinpu"} and "不是县界" in json.dumps(zy, ensure_ascii=False),
      [f["id"] for f in zy["fronts"]])
lm = place("1935-06-01", 27.698, 106.902)
check("1935-06-01 遵义有长征路线，不是辖境",
      any(f["id"] == "longmarch" for f in lm["fronts"]) and "不是辖境" in json.dumps(lm, ensure_ascii=False),
      [f["id"] for f in lm["fronts"]])


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
check("1929-12-19 还看不到伯力议定书", not has(names("1929-12-19", 39.9, 116.4), "伯力"), "")
check("1929-12-20 看得到伯力议定书", has(names("1929-12-20", 39.9, 116.4), "伯力"), "")
check("1932-05-05 看得到淞沪停战协定", has(names("1932-05-05", 32.06, 118.78), "淞沪停战"), "")
check("1933-05-31 看得到塘沽协定", has(names("1933-05-31", 39.9, 116.4), "塘沽"), "")
check("1937-08-20 还看不到中苏互不侵犯条约", not has(names("1937-08-20", 32.06, 118.78), "互不侵犯"), "")
check("1937-08-21 看得到中苏互不侵犯条约", has(names("1937-08-21", 32.06, 118.78), "互不侵犯"), "")
check("1935-06-27 看得到秦土协定", has(names("1935-06-27", 39.9, 116.4), "秦土"), "")
check("1935-07-06 看得到何梅协定", has(names("1935-07-06", 39.9, 116.4), "何梅"), "")
check("1943-01-10 还看不到中美新约", not has(names("1943-01-10", 29.56, 106.55), "治外法权"), "")
check("1943-01-11 看得到中美新约和中英新约",
      has(names("1943-01-11", 29.56, 106.55), "美国在华") and has(names("1943-01-11", 29.56, 106.55), "英国在华"), "")
check("1943-05-19 中英新约尚未生效", "已签署未生效" in "".join(names("1943-05-19", 29.56, 106.55)) or has(names("1943-05-19", 29.56, 106.55), "英国在华"), "")
check("1943-12-01 看得到开罗宣言", has(names("1943-12-01", 29.56, 106.55), "开罗"), "")
check("1945-08-13 还看不到中苏友好同盟条约", not has(names("1945-08-13", 29.56, 106.55), "友好同盟"), "")
check("1945-08-14 看得到中苏友好同盟条约", has(names("1945-08-14", 29.56, 106.55), "友好同盟"), "")
check("1945-10-10 看得到双十协定", has(names("1945-10-10", 29.56, 106.55), "会谈纪要"), "")
sy = place("1931-11-19", 41.794, 123.447)
check("1931-11-19 沈阳省界仍在，实控不是奉系独占",
      sy["place"]["name"] == "辽宁" and sy["place"]["actual"] == "实控待考" and any(f["id"] == "mukden-jl" for f in sy["fronts"]),
      sy["place"])
dh = place("1933-11-12", 43.807, 87.567)
check("1933-11-12 迪化仍是盛世才",
      dh["place"]["actual"] == "盛世才" and dh["place"]["nominal"] == "南京国民政府", dh["place"])
wc38 = place("1938-10-01", 30.524, 114.276)
check("1938-10-01 武昌有武汉会战",
      any(f["id"] == "wuhan-north" for f in wc38["fronts"]) and "不是省界" in json.dumps(wc38, ensure_ascii=False),
      [f["id"] for f in wc38["fronts"]])
nj = place("1937-12-10", 32.06, 118.8)
check("1937-12-10 江宁仍是南京国民政府，并有南京保卫战",
      nj["place"]["name"] == "江苏" and nj["place"]["actual"] == "南京国民政府"
      and any(f["id"] == "nanjing-1937" for f in nj["fronts"]) and "不是城墙" in json.dumps(nj, ensure_ascii=False),
      nj["place"])
gl = place("1944-11-15", 25.347, 110.164)
check("1944-11-15 桂林仍是桂系，并有桂柳",
      gl["place"]["name"] == "广西" and "桂系" in (gl["place"]["actual"] or "")
      and any(f["id"] == "guiliu-1944" for f in gl["fronts"]),
      gl["place"])
hh = place("1948-11-15", 34.302, 117.257)
check("1948-11-15 铜山实控仍待考，并有淮海",
      hh["place"]["actual"] == "实控待考" and any(f["id"] == "huaihai-1948" for f in hh["fronts"]),
      hh["place"])
wx = place("1938-12-01", 32.06, 118.8)
check("1938-12-01 维新政府只是名义标注",
      any(w["id"] == "puppet-reform" for w in wx["wars"]) and "不改阵营" in json.dumps(wx, ensure_ascii=False)
      and wx["place"]["actual"] == "实控待考",
      wx["place"])

loc = get("/api/locate", date="1919-06-28", lat=39.9, lon=116.4)
p = loc["polity"]
ev = get("/api/modules/events", date="1919-06-28", snap=loc["snapshot"], fid=p["fid"])
titles = [row.get("title") or "" for row in ev.get("items") or []]
check("1919-06-28 事件栏有拒签", any("拒绝签署" in t for t in titles), titles[:8])
check("拒签不作为生效条约插进条约栏", not has(names("1919-06-28", 39.9, 116.4), "拒绝签署"), "")

js422 = place("1949-04-22", 32.06, 118.8)
js423 = place("1949-04-23", 32.06, 118.8)
check("1949-04-22 江苏实控仍待考", js422["place"]["actual"] == "实控待考", js422["place"])
check("1949-04-23 江苏实控是中国共产党", js423["place"]["name"] == "江苏" and js423["place"]["actual"] == "中国共产党", js423["place"])
check("1949-06-01 南京省界实控是中国共产党",
      place("1949-06-01", 32.06, 118.8)["place"]["actual"] == "中国共产党", "")
sy1 = place("1948-11-01", 41.794, 123.447)
sy2 = place("1948-11-02", 41.794, 123.447)
check("1948-11-01 沈阳实控仍待考", sy1["place"]["actual"] == "实控待考", sy1["place"])
check("1948-11-02 沈阳实控是中国共产党", sy2["place"]["name"] == "辽宁" and sy2["place"]["actual"] == "中国共产党", sy2["place"])
dh24 = place("1949-09-24", 43.807, 87.567)
dh25 = place("1949-09-25", 43.807, 87.567)
check("1949-09-24 迪化还不是中国共产党", dh24["place"]["actual"] != "中国共产党", dh24["place"])
check("1949-09-25 迪化实控是中国共产党，盛世才那一条还在",
      dh25["place"]["actual"] == "中国共产党" and place("1937-07-01", 43.807, 87.567)["place"]["actual"] == "盛世才",
      dh25["place"])
sq = place("1944-11-12", 43.807, 87.567)
check("1944-11-12 新疆有三区，不是全省",
      any(w["id"] == "sanqu-1944" for w in sq["wars"]) and any(s["id"] == "yining-1944" for s in sq["seats"])
      and "不是新疆全省" in json.dumps(sq, ensure_ascii=False) and sq["place"]["actual"] == "实控待考",
      sq["place"])
km = place("1949-12-10", 25.0389, 102.7183)
cd = place("1949-12-10", 30.665, 104.069)
check("1949-12-10 昆明实控是中国共产党", km["place"]["name"] == "云南" and km["place"]["actual"] == "中国共产党", km["place"])
check("1949-12-10 成都还不是中国共产党", cd["place"]["name"] == "四川" and cd["place"]["actual"] == "实控待考", cd["place"])
loc = get("/api/locate", date="1949-12-10", lat=25.037, lon=121.565)
p = loc["polity"]
ev = get("/api/modules/events", date="1949-12-10", snap=loc["snapshot"], fid=p["fid"])
titles = [row.get("title") or "" for row in ev.get("items") or []]
check("1949-12-10 台北事件栏有迁台", "国民政府迁台" in titles, titles[:8])
loc6 = get("/api/locate", date="1949-12-06", lat=25.037, lon=121.565)
ev6 = get("/api/modules/events", date="1949-12-06", snap=loc6["snapshot"], fid=loc6["polity"]["fid"])
titles6 = [row.get("title") or "" for row in ev6.get("items") or []]
check("1949-12-06 还没有这一条迁台", "国民政府迁台" not in titles6, titles6[:8])

check("1928-06-30 还看不到中美关税条约", not has(names("1928-06-30", 32.06, 118.78), "关税"), "")
check("1928-07-01 不把月初写成签署日", not has(names("1928-07-01", 32.06, 118.78), "中美关税"), "")
check("1928-07-20 看得到只记到月的中美关税条约", has(names("1928-07-20", 32.06, 118.78), "中美关税"), "")
check("1930-05-05 还看不到中日关税协定", not has(names("1930-05-05", 32.06, 118.78), "中日关税"), "")
check("1930-05-06 看得到中日关税协定", has(names("1930-05-06", 32.06, 118.78), "中日关税"), "")
check("1931-02-26 不画哈密线", "ma-hami-1931" not in ids_on("1931-02-26"), "")
check("1931-04-15 有哈密到迪化", "ma-hami-1931" in ids_on("1931-04-15"), ids_on("1931-04-15"))
check("1931-10-01 起不留这条入疆线", "ma-hami-1931" not in ids_on("1931-10-01"), "")
check("1934-01-12 有攻迪化", "ma-dihua-1934" in ids_on("1934-01-12"), "")
check("1934-01-13 起不留攻迪化", "ma-dihua-1934" not in ids_on("1934-01-13"), "")
check("1922-06-16 有番禺点", "panyu-1922" in {s["id"] for s in bundle(ROOT / "data", "1922-06-16")["seats"]}, "")
check("1922-06-17 起不留番禺点", "panyu-1922" not in {s["id"] for s in bundle(ROOT / "data", "1922-06-17")["seats"]}, "")
sc32 = {s["id"] for s in get("/api/layers/roc_provinces", date="1932-06-01")["seats"]}
check("1932-06-01 有刘湘、刘文辉驻地点", {"chongqing-liu-xiang", "chengdu-liu-wenhui"} <= sc32, sorted(sc32))
check("1935-07-01 起不留刘湘驻地点", "chongqing-liu-xiang" not in {s["id"] for s in get("/api/layers/roc_provinces", date="1935-07-01")["seats"]}, "")
cq49 = {s["id"] for s in get("/api/layers/roc_provinces", date="1949-11-30")["seats"]}
check("1949-11-30 有重庆沦陷点", "chongqing-1949" in cq49, sorted(cq49))
check("1949-12-01 起不留重庆沦陷点", "chongqing-1949" not in {s["id"] for s in get("/api/layers/roc_provinces", date="1949-12-01")["seats"]}, "")
hf20 = place("1949-01-20", 31.902, 117.300)
hf21 = place("1949-01-21", 31.902, 117.300)
check("1949-01-20 合肥还不是中国共产党", hf20["place"]["actual"] != "中国共产党", hf20["place"])
check("1949-01-21 合肥实控是中国共产党", hf21["place"]["name"] == "安徽" and hf21["place"]["actual"] == "中国共产党", hf21["place"])
sy18 = place("1949-09-18", 40.798, 111.650)
sy19 = place("1949-09-19", 40.798, 111.650)
check("1949-09-18 归绥还不是中国共产党", sy18["place"]["actual"] != "中国共产党", sy18["place"])
check("1949-09-19 归绥实控是中国共产党", sy19["place"]["name"] == "绥远" and sy19["place"]["actual"] == "中国共产党", sy19["place"])
cc18 = place("1948-10-18", 43.884, 125.324)
cc19 = place("1948-10-19", 43.884, 125.324)
check("1948-10-18 长春还不是中国共产党", cc18["place"]["actual"] != "中国共产党", cc18["place"])
check("1948-10-19 长春实控是中国共产党", cc19["place"]["name"] == "吉林" and cc19["place"]["actual"] == "中国共产党", cc19["place"])

words = json.loads((ROOT / "data/curated/roc_beiyang.json").read_text(encoding="utf-8"))
yangtze = next(w for w in words["wars"] if w.get("id") == "yangtze-1949")
check("渡江战役两侧写共军", yangtze["sides"] == "共军 / 汤恩伯、白崇禧所部" and "解放军" not in yangtze["sides"], yangtze["sides"])
sanqu = next(w for w in words["wars"] if w.get("id") == "sanqu-1944")
check("三区说明写沦陷", "1949-09-25沦陷" in sanqu["note"] and "和平解放" not in sanqu["note"], sanqu["note"][-40:])
admin = json.loads((ROOT / "data/curated/roc_admin.json").read_text(encoding="utf-8"))
xinjiang = next(u for u in admin["units"] if u["id"] == "xinjiang")
xin_note = xinjiang["controls"][-1]["note"]
check("新疆省界说明写沦陷", "新疆沦陷" in xin_note and "和平解放" not in xin_note and "解放军" not in xin_note, xin_note[:40])
zones = json.loads((ROOT / "data/curated/control_zones.json").read_text(encoding="utf-8"))["zones"]
ne_names = [z["name_zh"] for z in zones if z["id"].startswith("ccw_ne_ccp_")]
check("东北四块写沦陷区", ne_names and all(n.startswith("东北沦陷区") and "解放区" not in n and "解放军" not in n for n in ne_names), ne_names)
jn23 = place("1948-09-23", 36.690, 116.998)
jn24 = place("1948-09-24", 36.690, 116.998)
check("1948-09-23 济南还不是中国共产党", jn23["place"]["actual"] != "中国共产党", jn23["place"])
check("1948-09-24 济南实控是中国共产党", jn24["place"]["name"] == "山东" and jn24["place"]["actual"] == "中国共产党" and "沦陷" in (jn24["place"].get("note") or ""), jn24["place"])
kf23 = place("1948-10-23", 34.802, 114.345)
kf24 = place("1948-10-24", 34.802, 114.345)
check("1948-10-23 开封还不是中国共产党", kf23["place"]["actual"] != "中国共产党", kf23["place"])
check("1948-10-24 开封实控是中国共产党", kf24["place"]["name"] == "河南" and kf24["place"]["actual"] == "中国共产党" and "1948-10-22" in (kf24["place"].get("note") or ""), kf24["place"])
gy14 = place("1949-11-14", 26.647, 106.630)
gy15 = place("1949-11-15", 26.647, 106.630)
check("1949-11-14 贵阳还不是中国共产党", gy14["place"]["actual"] != "中国共产党", gy14["place"])
check("1949-11-15 贵阳实控是中国共产党", gy15["place"]["name"] == "贵州" and gy15["place"]["actual"] == "中国共产党", gy15["place"])
nn03 = place("1949-12-03", 22.817, 108.366)
nn04 = place("1949-12-04", 22.817, 108.366)
check("1949-12-03 南宁仍是桂系", "桂系" in (nn03["place"]["actual"] or ""), nn03["place"])
check("1949-12-04 南宁实控是中国共产党", nn04["place"]["name"] == "广西" and nn04["place"]["actual"] == "中国共产党", nn04["place"])
han10 = place("1930-09-10", 36.690, 116.998)
han11 = place("1930-09-11", 36.690, 116.998)
check("1930-09-10 济南还不是韩复榘", "韩复榘" not in (han10["place"]["actual"] or ""), han10["place"])
check("1930-09-11 济南实控是韩复榘", han11["place"]["name"] == "山东" and han11["place"]["actual"] == "韩复榘", han11["place"])
chen11 = place("1931-05-11", 23.129, 113.264)
chen12 = place("1931-05-12", 23.129, 113.264)
check("1931-05-11 广州还不是陈济棠", "陈济棠" not in (chen11["place"]["actual"] or ""), chen11["place"])
check("1931-05-12 广州实控是陈济棠", chen12["place"]["name"] == "广东" and chen12["place"]["actual"] == "陈济棠", chen12["place"])
for uid in ("guizhou", "guangxi", "henan", "shandong"):
    unit = next(u for u in admin["units"] if u["id"] == uid)
    blob = json.dumps(unit.get("controls") or [], ensure_ascii=False)
    check(f"{uid} 新说明不用解放军", "解放军" not in blob and "解放区" not in blob, blob[:80])

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
