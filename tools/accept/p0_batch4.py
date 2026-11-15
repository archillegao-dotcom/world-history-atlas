"""第四批：四份法国文件的签署/生效，以及 1950 年沿海与李弥部。
1911 年分省独立没有做。用法：WHA_PORT=8792 python3 tools/accept/p0_batch4.py
"""
import json, os, sys, urllib.parse, urllib.request
B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"

def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=180))

def regime(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    if not p:
        return {"poly": None, "qid": None, "name": None}
    d = get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=p["fid"])
    st = d.get("state") or {}
    return {"poly": p.get("NAME_ZH") or p.get("NAME"), "qid": st.get("id"), "name": st.get("name")}

def spirits(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc["polity"]
    return get("/api/modules/spirits", date=date, snap=loc["snapshot"], fid=p["fid"])

def names(sp, bucket):
    return [c["name"] for c in sp.get(bucket) or []]

fails = []
def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:180])
    if not cond:
        fails.append(label)

# 意大利：6 月 24 日已签署未生效，25 日才进入「未记录终止」。
r24 = spirits("1940-06-24", 41.9, 12.5)
r25 = spirits("1940-06-25", 41.9, 12.5)
check("6月24日法意停战在尚未生效", "法国-意大利停战协定" in names(r24, "pending") and "法国-意大利停战协定" not in names(r24, "open"), names(r24, "pending"))
check("6月25日法意停战已过生效日", "法国-意大利停战协定" in names(r25, "open") and "法国-意大利停战协定" not in names(r25, "pending"), names(r25, "open"))

# 6 月 22 日地图把法国标成德军占领区。文件应出现在「尚未生效」，签署方仍是第三共和国。
fr = spirits("1940-06-22", 46.13, 3.42)
check("6月22日贡比涅停战尚未生效", "第二次贡比涅停战协定" in names(fr, "pending"), names(fr, "pending"))
check("6月22日不把法意停战提前放上", "法国-意大利停战协定" not in names(fr, "pending") + names(fr, "open"), names(fr, "pending"))
card = next(c for c in fr["pending"] if c["name"] == "第二次贡比涅停战协定")
check("占领区不是贡比涅签署方", "不是签署方" in (card.get("role") or ""), card.get("role"))

# 维希沿用，巴黎议定书未批准，7 月 29 日议定书不进生效列表。
vy = spirits("1941-06-01", 46.2, 2.4)
check("维希看到巴黎议定书未批准", "巴黎议定书" in names(vy, "unratified") and "巴黎议定书" not in names(vy, "open") + names(vy, "dated"), names(vy, "unratified"))
check("6月1日还没有法日议定书", "法日印度支那议定书" not in names(vy, "implemented"), names(vy, "implemented"))
vy2 = spirits("1941-07-29", 46.2, 2.4)
check("7月29日法日议定书在公布实施栏", "法日印度支那议定书" in names(vy2, "implemented") and "法日印度支那议定书" not in names(vy2, "open") + names(vy2, "dated"), names(vy2, "implemented"))
arm = next(c for c in vy["open"] if c["name"] == "第二次贡比涅停战协定")
check("维希沿用贡比涅文件", "不是签署方" in (arm.get("role") or ""), arm.get("role"))

t = get("/api/treaty/Q170360")
check("贡比涅签署方是第三共和国和德国", [p["name"] for p in t["parties"]] == ["法兰西第三共和国", "纳粹德国"], [p["name"] for p in t["parties"]])
check("贡比涅类型是停战协定", t.get("kind") == "停战协定" and t.get("effective") == "1940年6月25日", f"{t.get('kind')} {t.get('effective')}")
tp = get("/api/treaty/curated:paris-protocols-1941")
check("巴黎议定书无生效日", tp.get("kind") == "议定书" and not tp.get("effective") and "未获批准" in (tp.get("status_zh") or ""), tp.get("status_zh"))

# 1950 沿海。整岛不再是中华民国。
check("3月海口是城市框", "海口" in (regime("1950-03-01", 20.04, 110.32)["poly"] or ""), regime("1950-03-01", 20.04, 110.32))
check("4月23日海口已换手", regime("1950-04-23", 20.04, 110.32)["qid"] == "Q148", regime("1950-04-23", 20.04, 110.32))
check("海南腹地不是整岛中华民国框", "海南岛（中华民国控制）" not in (regime("1950-03-01", 19.2, 109.7)["poly"] or ""), regime("1950-03-01", 19.2, 109.7))
check("4月29日三亚一带仍在框内", "三亚" in (regime("1950-04-29", 18.25, 109.51)["poly"] or ""), regime("1950-04-29", 18.25, 109.51))
check("4月30日三亚一带已换手", regime("1950-04-30", 18.25, 109.51)["qid"] == "Q148", regime("1950-04-30", 18.25, 109.51))
check("5月16日舟山岛上仍是中华民国", regime("1950-05-16", 30.04, 122.1489)["qid"] in ("Q865", "Q13426199"), regime("1950-05-16", 30.04, 122.1489))
check("5月17日舟山已换手", (regime("1950-05-17", 30.04, 122.1489)["qid"] or "") not in ("Q865", "Q13426199"), regime("1950-05-17", 30.04, 122.1489))
check("一江山1月19日是大致范围", "一江山" in (regime("1955-01-19", 28.62, 121.82)["poly"] or ""), regime("1955-01-19", 28.62, 121.82))
lay20 = [i["name"] for i in get("/api/layers/control_zones", date="1955-01-20")["items"]]
check("1月20日图层不再画一江山", not any("一江山" in n for n in lay20), [n for n in lay20 if "江" in n or "大陈" in n])
check("2月11日大陈仍在", "大陈" in (regime("1955-02-11", 28.45, 121.90)["poly"] or ""), regime("1955-02-11", 28.45, 121.90))
d12 = regime("1955-02-12", 28.45, 121.90)
check("2月12日大陈不再是中华民国", (d12["qid"] or "") not in ("Q865", "Q13426199"), d12)
check("金门仍经台湾多边形回到中华民国", regime("1950-06-01", 24.45, 118.32)["qid"] in ("Q865", "Q13426199"), regime("1950-06-01", 24.45, 118.32))
check("昆明不是李弥部主权", regime("1951-06-01", 25.04, 102.68)["qid"] == "Q148", regime("1951-06-01", 25.04, 102.68))
lim = regime("1951-06-01", 20.8, 99.3)
check("景栋一带点击不是中华民国主权", (lim["qid"] or "") not in ("Q865", "Q13426199"), lim)
lay_items = get("/api/layers/control_zones", date="1951-06-01")["items"]
limi = next((i for i in lay_items if "李弥" in i["name"]), None)
check("1951年图层仍有李弥部且写明不是全省主权", bool(limi) and "不是主权" in (limi.get("note") or "") and "不是云南" in (limi.get("note") or ""), (limi or {}).get("note"))
check("只选1950年不显示已在5月换手的舟山", not any("舟山" in i["name"] for i in get("/api/layers/control_zones", date="1950")["items"]), "year-only")
# 已有修复不要退回去
check("1949-11-15桂林仍是广西中华民国控制区", "广西" in (regime("1949-11-15", 25.27, 110.29)["poly"] or ""), regime("1949-11-15", 25.27, 110.29))
check("1946台北仍是中华民国", regime("1946-06-01", 25.037, 121.564)["qid"] in ("Q865", "Q13426199"), regime("1946-06-01", 25.037, 121.564))
check("1949-10-15广州仍是中华人民共和国", regime("1949-10-15", 23.13, 113.26)["qid"] == "Q148", regime("1949-10-15", 23.13, 113.26))
h = get("/api/econ_hover", date="2000-06-01", snap=get("/api/locate", date="2000-06-01", lat=48.86, lon=2.35)["snapshot"], fid=get("/api/locate", date="2000-06-01", lat=48.86, lon=2.35)["polity"]["fid"])
check("悬停说明是现代国家范围且来源只写一次", "现代国家范围" in h["note"] and h["note"].count("Maddison") == 1 and "不是当时政权" in h["note"], h["note"][:80])
print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
