"""第三批：SOLAS 按版本分开。1951-03-16 只看见当时已经签署的版本。

用法：WHA_PORT=8792 python3 tools/accept/next_batch3.py
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    q = "?" + urllib.parse.urlencode(kw) if kw else ""
    return json.load(urllib.request.urlopen(B + path + q, timeout=180))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:220])
    if not cond:
        fails.append(label)


def spirits(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc["polity"]
    return get("/api/modules/spirits", date=date, snap=loc["snapshot"], fid=p["fid"])


def names(sp, *buckets):
    out = []
    for b in buckets:
        out += [c["name"] for c in sp.get(b) or []]
    return out


def blob(obj):
    return json.dumps(obj, ensure_ascii=False)


LONDON = (51.51, -0.13)
uk = spirits("1951-03-16", *LONDON)
shown = names(uk, "pending", "never", "dated", "open")
check("1951 英国面板有 1948 年版", "1948年国际海上人命安全公约" in names(uk, "pending"), names(uk, "pending"))
check("1951 1948 年版标成已签署未生效", any(
    c["name"] == "1948年国际海上人命安全公约" and c.get("status_zh") == "已签署未生效"
    for c in uk.get("pending") or []), names(uk, "pending"))
check("1951 1929 年版仍在有效期内", "1929年国际海上人命安全公约" in names(uk, "dated", "open"), shown)
check("1951 面板没有 1974 年版", not any("1974" in n for n in shown), shown)
check("1951 面板没有 1960 或 1988", not any(("1960" in n or "1988" in n) for n in shown), shown)
check("1951 面板文本没有 1980", "1980" not in blob(uk), "1980" in blob(uk))

t48 = get("/api/treaty/curated:solas-1948", date="1951-03-16")
text48 = blob(t48)
check("1951 弹窗生效日是 1952年11月19日", t48.get("effective") == "1952年11月19日", t48.get("effective"))
check("1951 弹窗效力是已签署未生效", t48.get("view_status") == "已签署未生效", t48.get("view_status"))
check("1951 弹窗不写 1965 年的取代日", t48.get("end_hidden") is True and not t48.get("end"), t48.get("end"))
check("1951 弹窗没有 1974", "1974" not in text48, "1974" in text48)
check("1951 弹窗没有 1980", "1980" not in text48, "1980" in text48)
check("1951 弹窗写明 1951年1月1日不是生效日", "不是实际生效日" in text48, t48.get("desc"))
check("1951 弹窗缔约方有英国且没有中华人民共和国",
      any(p.get("name") == "英国" for p in t48.get("parties") or [])
      and not any(p.get("name") == "中华人民共和国" for p in t48.get("parties") or []),
      [p.get("name") for p in t48.get("parties") or []])

t74 = get("/api/treaty/curated:solas-1974", date="1951-03-16")
check("1951 直接打开 1974 年版不给正文和生效日", t74.get("withhold") is True and not t74.get("effective") and not t74.get("summary"),
      {k: t74.get(k) for k in ("withhold", "effective", "view_status")})
check("1951 的 1974 响应没有 1980", "1980" not in blob(t74), blob(t74)[:180])

t13 = get("/api/treaty/curated:solas-1914", date="1914-06-01")
check("1914 年版没有写成已经生效", t13.get("effective") in (None, "") and "没有生效" in blob(t13), t13.get("effective"))
check("1914 年版不写 1980", "1980" not in blob(t13), "1980" in blob(t13))

try:
    urllib.request.urlopen(B + "/api/treaty/Q523582", timeout=60)
    check("混写的 Q523582 不再提供", False, "200")
except urllib.error.HTTPError as e:
    check("混写的 Q523582 不再提供", e.code == 404, e.code)

after = get("/api/treaty/curated:solas-1974", date="1980-05-25")
check("1980-05-25 才显示 1974 年版生效", after.get("effective") == "1980年5月25日" and not after.get("withhold"), after.get("effective"))
check("1974 年版摘要不收录后来增订的章节年", "2024" not in (after.get("desc") or "") and "2016" not in (after.get("desc") or ""), after.get("desc"))

p78 = get("/api/treaty/curated:solas-1978", date="1978-06-01")
check("1978 议定书在生效前标已签署未生效", p78.get("view_status") == "已签署未生效" and p78.get("effective") == "1981年5月1日", p78.get("view_status"))
p88 = get("/api/treaty/curated:solas-1988", date="1988-11-11")
check("1988 议定书通过日是 1988年11月11日", p88.get("adopted") == "1988年11月11日" and p88.get("view_status") == "已签署未生效", p88.get("adopted"))

print("FAILS", len(fails))
sys.exit(1 if fails else 0)
