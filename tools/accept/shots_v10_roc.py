"""
用户式截图（screenshots/v09b：v0.6.1 君主空档核对的新结果）：像用户一样在顶栏输入年份、选月/日（或不选）、点「跳转」，平移到目标位置后点击地图，必要时切换面板标签，然后截图。
同时把面板标题与正文前 300 字记入 logs/shots_v09.json，便于核对。
用法：.venv/bin/python tools/accept/shots_v08.py [名称过滤]
"""
import json, sys
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8792"
OUT = "screenshots/v10_roc"
LOGF = "logs/shots_v10_roc.json"
# 名称, 年(负=公元前), 月(0=不选), 日, 纬度, 经度, 缩放, 标签（None=默认）
S = [   # t88u：中华民国 1912–1950 关键节点（东北/华北/华中/海南），点击位置写在名称里
    ("01_1928-12_沈阳_东北易帜后", 1928, 12, 31, 41.8, 123.43, 4.5, None),
    ("02_1932-06_哈尔滨_满洲国", 1932, 6, 15, 45.75, 126.65, 4.5, None),
    ("03_1932-06_黑河_满洲国", 1932, 6, 15, 49.9, 127.2, 4.5, None),
    ("04_1937-12_南京_日军占领", 1937, 12, 20, 32.06, 118.8, 4.5, None),
    ("05_1938-10_武汉", 1938, 10, 31, 30.59, 114.3, 4.5, None),
    ("06_1940-11_哈尔滨_单一满洲国", 1940, 11, 2, 45.75, 126.65, 4.5, None),
    ("07_1940-11_南京_汪精卫政权", 1940, 11, 2, 32.06, 118.8, 4.5, None),
    ("08_1940-11_重庆_国民政府", 1940, 11, 2, 29.56, 106.55, 4.5, None),
    ("09_1944-12_桂林_一号作战后", 1944, 12, 15, 25.27, 110.29, 4.5, None),
    ("10_1945-09_南京", 1945, 9, 15, 32.06, 118.8, 4.5, None),
    ("11_1947-06_延安", 1947, 6, 15, 36.6, 109.49, 4.5, None),
    ("12_1949-10_广州", 1949, 10, 10, 23.13, 113.26, 4.5, None),
    ("13_1950-03_海口", 1950, 3, 15, 20.03, 110.33, 6, None),
    ("14_1950-06_海口", 1950, 6, 15, 20.03, 110.33, 6, None),
    ("15_1950-03_舟山", 1950, 3, 15, 30.05, 122.2, 7, None),
    ("16_1940-11_莫斯科_苏联单色", 1940, 11, 2, 55.75, 37.62, 3, None),
]
flt = sys.argv[1] if len(sys.argv) > 1 else None
log = []
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    bad = []   # 4xx/5xx 与失败请求的完整 URL（v0.6.1：排查控制台 404）
    pg.on("response", lambda r: r.status >= 400 and bad.append(f"{r.status} {r.url}"))
    pg.on("requestfailed", lambda r: bad.append(f"failed {r.url} {r.failure}"))
    pg.goto(B + "/"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2000)
    for name, y, m, d, lat, lon, z, tab in S:
        if flt and not any(x in name for x in flt.split(",")):
            continue
        pg.evaluate("WHA.map.closePopup && WHA.map.closePopup()")
        pg.set_checked("#isBC", y < 0)
        pg.fill("#yearIn", str(abs(y)))
        pg.select_option("#monthIn", str(m))
        if m:
            pg.select_option("#dayIn", str(d))
        pg.click("#goBtn")
        pg.wait_for_timeout(1200); pg.wait_for_load_state("networkidle")
        for _ in range(900):   # 等新日期的边界加载完（setDate 最后才 updateHash），最多 90 秒；否则会点到上一个日期的多边形
            if pg.evaluate("location.hash.includes('date=' + WHA.dateParam() + '&') || location.hash.endsWith('date=' + WHA.dateParam())"):
                break
            pg.wait_for_timeout(100)
        # v0.6.1：再确认前端已换到新日期对应的边界快照（否则会点到上一快照的多边形编号，如 1950 科威特截图）
        exp = pg.evaluate("WHA.api('/api/snapshot?date=' + WHA.dateParam()).then((r) => String(r.snapshot))")
        for _ in range(600):
            if pg.evaluate("String(WHA.state.snap)") == exp:
                break
            pg.wait_for_timeout(100)
        pg.evaluate(f"WHA.map.setView([{lat},{lon}], {z}, {{animate:false}})")
        pg.wait_for_timeout(3000); pg.wait_for_load_state("networkidle")
        pt = pg.evaluate(f"(() => {{ const q = WHA.map.latLngToContainerPoint([{lat},{lon}]); const r = document.getElementById('map').getBoundingClientRect(); return [q.x + r.left, q.y + r.top]; }})()")
        pg.evaluate("document.getElementById('polityName').textContent = ''")
        pg.mouse.click(*pt)
        for _ in range(400):   # 1886 年以后的边界渲染慢：等面板标题出现，最多 40 秒
            pg.wait_for_timeout(100)
            if pg.evaluate("document.getElementById('polityName').textContent").strip() not in ("", "—"):
                break
        pg.wait_for_timeout(2500); pg.wait_for_load_state("networkidle")
        if tab:
            pg.locator("#tabs button", has_text=tab).first.click()
            pg.wait_for_timeout(2000)
        pg.mouse.move(5, 300)
        pg.wait_for_timeout(400)
        pg.screenshot(path=f"{OUT}/{name}.png")
        title = pg.inner_text("#polityName")
        body = pg.inner_text("#tabBody")[:300]
        label = pg.inner_text("#dateLabel")
        log.append({"shot": f"{OUT}/{name}.png", "date_label": label, "title": title, "body": body})
        print(name, "|", label, "|", title, "|", body[:120].replace("\n", " "), flush=True)
    br.close()
LOG = globals().get("LOGF", "logs/shots_v09.json")
if flt:   # 只重拍部分截图时，合并进原记录
    try:
        old = json.load(open(LOG)); keep = [x for x in old["shots"] if x["shot"] not in {y["shot"] for y in log}]
        log = sorted(keep + log, key=lambda x: x["shot"])
    except Exception:
        pass
json.dump({"shots": log, "console_errors": errs[:50], "bad_responses": bad}, open(LOG, "w"), ensure_ascii=False, indent=1)
print("console errors:", len(errs), "bad responses:", len(bad)); print("\n".join(bad[:30]))
