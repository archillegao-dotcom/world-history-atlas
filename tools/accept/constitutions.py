"""宪法页按日验收。对运行中的 8792 做前后一日查询。"""
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
        for part in it.get("parts") or []:
            out.append(part.get("title") or "")
    return out

def prose(body):
    bits = [body.get("note") or "", body.get("coverage") or ""]
    for it in body.get("items") or []:
        for k in ("summary", "force_zh", "force_note", "day_note", "effective_clause", "effective_clause_orig"):
            bits.append(it.get(k) or "")
        if it.get("effective"):
            bits.append("生效：" + it["effective"])
        for part in it.get("parts") or []:
            bits.append(part.get("summary") or "")
            bits.append(part.get("since_note") or "")
    return "\n".join(bits)

def check(why, date, lat, lon, present=(), absent=(), shown=None, note_has=None, say=(), unsay=()):
    p, body = law(date, lat, lon)
    if body is None:
        fails.append(why + " 没有点到多边形")
        return
    got = names(body)
    blob = " ".join(got)
    note = body.get("note") or ""
    text = prose(body)
    bad = []
    if shown is not None and bool(body.get("shown")) != shown:
        bad.append(f"shown={body.get('shown')} 期望 {shown}")
    for t in present:
        if t not in blob:
            bad.append(f"缺少 {t}")
    for t in absent:
        if t in blob:
            bad.append(f"不该出现 {t}")
    for t in say:
        if t not in text:
            bad.append(f"说明缺少「{t}」")
    for t in unsay:
        if t in text:
            bad.append(f"说明不该有「{t}」")
    if note_has and note_has not in note and note_has not in (body.get("coverage") or ""):
        bad.append(f"说明里没有「{note_has}」")
    if "无宪法" in (note + blob + text):
        bad.append("出现了「无宪法」")
    if bad:
        fails.append(why + " " + "；".join(bad) + " 实际=" + "、".join(x for x in got if x))
    print(("?? " if bad else "OK ") + why + " → " + ("、".join(x for x in got if x) or "（无页）"))

# 法国
check("1944-12-01 巴黎是临时政府法令，不是1946宪法", "1944-12-01", 48.8566, 2.3522,
      present=["1944年8月9日恢复共和合法性法令"], absent=["1946年10月27日宪法", "1958年10月4日宪法", "1945年11月2日宪法性法律"], shown=True)
check("1945-11-01 巴黎仍只有8月9日法令", "1945-11-01", 48.8566, 2.3522,
      present=["1944年8月9日恢复共和合法性法令"], absent=["1945年11月2日宪法性法律", "1946年10月27日宪法"], shown=True)
check("1945-11-02 巴黎同时有两部临时文本", "1945-11-02", 48.8566, 2.3522,
      present=["1944年8月9日恢复共和合法性法令", "1945年11月2日宪法性法律"], absent=["1946年10月27日宪法"], shown=True)
check("1946-10-26 巴黎还不是1946宪法", "1946-10-26", 48.8566, 2.3522,
      present=["1945年11月2日宪法性法律"], absent=["1946年10月27日宪法"], shown=True)
check("1946-10-27 巴黎是1946宪法", "1946-10-27", 48.8566, 2.3522,
      present=["1946年10月27日宪法"], absent=["1944年8月9日恢复共和合法性法令", "1958年10月4日宪法"], shown=True)
check("1958-10-03 巴黎仍是1946宪法", "1958-10-03", 48.8566, 2.3522,
      present=["1946年10月27日宪法"], absent=["1958年10月4日宪法"], shown=True)
check("1958-10-04 巴黎是1958宪法", "1958-10-04", 48.8566, 2.3522,
      present=["1958年10月4日宪法"], absent=["1946年10月27日宪法"], shown=True)
check("1875-02-24 巴黎还没有整组1875年法律", "1875-02-24", 48.8566, 2.3522,
      absent=["1875年宪法性法律"], shown=True)
check("1875-02-25 巴黎是1875年宪法性法律", "1875-02-25", 48.8566, 2.3522,
      present=["1875年宪法性法律"], shown=True)
check("1848-11-03 巴黎还不是1848年宪法", "1848-11-03", 48.8566, 2.3522,
      absent=["1848年宪法"], shown=True)
check("1848-11-04 巴黎是1848年宪法", "1848-11-04", 48.8566, 2.3522,
      present=["1848年宪法"], shown=True)
check("1852-01-13 巴黎仍是1848年宪法", "1852-01-13", 48.8566, 2.3522,
      present=["1848年宪法"], shown=True)
check("1852-01-14 巴黎不再显示1848年宪法", "1852-01-14", 48.8566, 2.3522,
      absent=["1848年宪法"], shown=True)
check("1940-06-01 巴黎仍是1875年法律", "1940-06-01", 48.8566, 2.3522,
      present=["1875年宪法性法律"], absent=["维希宪法性法令"], shown=True)
check("1940-07-09 维希底图仍显示1875年法律", "1940-07-09", 46.127, 3.426,
      present=["1875年宪法性法律"], absent=["1940年7月10日宪法性法律", "1940年7月11日宪法性法令"], shown=True)
check("1940-07-09 巴黎占领区不套法国宪法", "1940-07-09", 48.8566, 2.3522,
      absent=["1875年宪法性法律", "1940年7月10日宪法性法律", "1946年10月27日宪法"], shown=True, note_has="已核对")
check("1940-07-10 巴黎占领区不套法国宪法", "1940-07-10", 48.8566, 2.3522,
      absent=["1875年宪法性法律", "1940年7月10日宪法性法律", "1946年10月27日宪法"], shown=True, note_has="已核对")
check("1940-07-10 维希同时有1875年法律和7月10日授权", "1940-07-10", 46.127, 3.426,
      present=["1875年宪法性法律", "1940年7月10日宪法性法律"], absent=["1940年7月11日宪法性法令"], shown=True)
check("1940-07-11 维希改列7月11日法令", "1940-07-11", 46.127, 3.426,
      present=["1940年7月10日宪法性法律", "1940年7月11日宪法性法令", "类型待考"], absent=["1875年宪法性法律"], shown=True)
check("1942-06-01 里昂仍分列两部维希文本", "1942-06-01", 45.764, 4.835,
      present=["1940年7月10日宪法性法律", "1940年7月11日宪法性法令", "类型待考"], absent=["1946年10月27日宪法", "1875年宪法性法律"], shown=True)

# 德国
check("1919-08-13 魏玛还没生效", "1919-08-13", 50.98, 11.32,
      absent=["魏玛宪法"], shown=True)
check("1919-08-14 魏玛生效", "1919-08-14", 50.98, 11.32,
      present=["魏玛宪法"], shown=True)
check("1933-01-29 柏林仍是魏玛宪法", "1933-01-29", 52.52, 13.405,
      present=["魏玛宪法"], shown=True)
check("1933-02-27 柏林还没有2月28日命令", "1933-02-27", 52.52, 13.405,
      present=["魏玛宪法"], absent=["1933年2月28日保护人民与国家令", "1933年3月24日授权法"], shown=True)
check("1933-02-28 柏林列出停止基本权利的命令", "1933-02-28", 52.52, 13.405,
      present=["魏玛宪法", "1933年2月28日保护人民与国家令"], absent=["1933年3月24日授权法"], shown=True,
      say=["形式未废止，列出的基本权利已停止"])
check("1933-03-23 柏林仍未到授权法公布日", "1933-03-23", 52.52, 13.405,
      present=["魏玛宪法", "1933年2月28日保护人民与国家令"], absent=["1933年3月24日授权法", "德意志联邦共和国基本法"], shown=True)
check("1933-03-24 柏林仍列魏玛宪法并说明被架空", "1933-03-24", 52.52, 13.405,
      present=["魏玛宪法", "1933年3月24日授权法", "相关法律，不是新宪法"], absent=["德意志联邦共和国基本法"], shown=True,
      say=["形式未废止，实际被架空"])
check("1944-12-01 柏林仍列被架空的魏玛宪法", "1944-12-01", 52.52, 13.405,
      present=["魏玛宪法", "1933年3月24日授权法"], absent=["德意志联邦共和国基本法"], shown=True,
      say=["形式未废止，实际被架空"])
check("1949-05-23 波恩显示基本法并保留结束时生效", "1949-05-23", 50.737, 7.1,
      present=["德意志联邦共和国基本法", "基本法"], shown=True,
      say=["于公布当日结束时生效", "不把5月23日全天写成尚未生效"],
      unsay=["生效：1949-05-24"])
check("1949-05-24 波恩不把次日写成法定生效日", "1949-05-24", 50.737, 7.1,
      present=["德意志联邦共和国基本法", "基本法"], shown=True,
      say=["不是另定的生效日期", "于公布当日结束时生效"])
check("1949-05-24 柏林苏占区不是基本法", "1949-05-24", 52.52, 13.405,
      absent=["德意志联邦共和国基本法", "德意志民主共和国1949年宪法"], shown=True, note_has="已核对")
check("1949-10-06 柏林还不是东德宪法", "1949-10-06", 52.52, 13.405,
      absent=["德意志民主共和国1949年宪法", "德意志联邦共和国基本法"], shown=True)
check("1949-10-07 柏林是东德1949年宪法", "1949-10-07", 52.52, 13.405,
      present=["德意志民主共和国1949年宪法"], absent=["德意志联邦共和国基本法"], shown=True)
check("1968-04-05 柏林仍是东德1949年宪法", "1968-04-05", 52.52, 13.405,
      present=["德意志民主共和国1949年宪法"], shown=True)
check("1968-04-06 柏林不再显示1949年宪法", "1968-04-06", 52.52, 13.405,
      absent=["德意志民主共和国1949年宪法", "德意志联邦共和国基本法"], shown=True)
check("1990-10-02 波恩仍是基本法", "1990-10-02", 50.737, 7.1,
      present=["德意志联邦共和国基本法"], shown=True)
check("1990-10-03 柏林统一后仍是基本法", "1990-10-03", 52.52, 13.405,
      present=["德意志联邦共和国基本法"], absent=["德意志民主共和国1949年宪法"], shown=True)

# 日本
check("1890-11-28 东京还没施行帝国宪法", "1890-11-28", 35.69, 139.69,
      absent=["大日本帝国宪法", "日本国宪法"], shown=True)
check("1890-11-29 东京施行帝国宪法", "1890-11-29", 35.69, 139.69,
      present=["大日本帝国宪法", "帝国/钦定宪法"], absent=["日本国宪法"], shown=True)
check("1944-12-01 东京是帝国宪法不是1947宪法", "1944-12-01", 35.69, 139.69,
      present=["大日本帝国宪法"], absent=["日本国宪法"], shown=True)
check("1947-05-02 东京仍是帝国宪法", "1947-05-02", 35.69, 139.69,
      present=["大日本帝国宪法"], absent=["日本国宪法"], shown=True)
check("1947-05-03 东京是日本国宪法", "1947-05-03", 35.69, 139.69,
      present=["日本国宪法"], absent=["大日本帝国宪法"], shown=True,
      say=["六个月经过之后的那一天起施行", "条文里没有写1947年5月3日"],
      unsay=["满六个月的那一天施行，即1947年5月3日"])

# 英国
check("1800-12-31 伦敦没有对应到联合王国条目", "1800-12-31", 51.5074, -0.1276,
      absent=["不成文宪法", "1911年议会法"], shown=True, note_has="没有对应")
check("1801-01-01 伦敦是不成文宪法", "1801-01-01", 51.5074, -0.1276,
      present=["不成文宪法", "1688年权利法案", "1800年与爱尔兰合并法"], absent=["1911年议会法", "1949年议会法"], shown=True,
      say=["不是这套不成文制度的起始日", "不回推1688年的英格兰"])
check("1911-08-17 伦敦还没有1911年议会法", "1911-08-17", 51.5074, -0.1276,
      present=["不成文宪法"], absent=["1911年议会法"], shown=True)
check("1911-08-18 伦敦列入1911年议会法", "1911-08-18", 51.5074, -0.1276,
      present=["不成文宪法", "1911年议会法"], absent=["1949年议会法"], shown=True)
check("1949-12-15 伦敦还没有1949年议会法", "1949-12-15", 51.5074, -0.1276,
      present=["1911年议会法"], absent=["1949年议会法"], shown=True)
check("1949-12-16 伦敦列入1949年议会法", "1949-12-16", 51.5074, -0.1276,
      present=["不成文宪法", "1949年议会法"], shown=True)
check("1944-12-01 德里不套英国不成文宪法", "1944-12-01", 28.6, 77.2,
      absent=["不成文宪法", "1911年议会法"], shown=True, note_has="没有收录")
check("2000-06-01 伦敦仍是不成文宪法", "2000-06-01", 51.5074, -0.1276,
      present=["不成文宪法", "1949年议会法"], shown=True)

# 不把没做的政权写成无宪法
check("1944-12-01 重庆不编中华民国宪法", "1944-12-01", 29.56, 106.55,
      absent=["1946年10月27日宪法", "日本国宪法"], shown=True, say=["没有收录", "不等于"])
check("2000-06-01 北京不编中华人民共和国宪法", "2000-06-01", 39.9, 116.4,
      absent=["德意志联邦共和国基本法", "日本国宪法"], shown=True, say=["没有收录", "不等于"])

print(f"FAIL {len(fails)}")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
