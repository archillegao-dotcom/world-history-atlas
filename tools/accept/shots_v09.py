"""
用户式截图（screenshots/v09）：像用户一样在顶栏输入年份、选月/日（或不选）、点「跳转」，平移到目标位置后点击地图，必要时切换面板标签，然后截图。
同时把面板标题与正文前 300 字记入 logs/shots_v09.json，便于核对。
用法：.venv/bin/python tools/accept/shots_v08.py [名称过滤]
"""
import json, sys
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8792"
OUT = "screenshots/v09"
# 名称, 年(负=公元前), 月(0=不选), 日, 纬度, 经度, 缩放, 标签（None=默认）
S = [
    # 空位期 / 摄政 / 共治（任务 A）
    ("01_前841_周_共和_领导人", -841, 0, 0, 34.26, 108.94, 4.5, "领导人"),
    ("02_前74_西汉_霍光_领导人", -74, 0, 0, 34.26, 108.94, 4.5, "领导人"),
    ("03_1333_元_空位_领导人", 1333, 0, 0, 39.9, 116.4, 4.5, "领导人"),
    ("04_1650_英格兰共和_国务会议_领导人", 1650, 0, 0, 51.5, -0.12, 5, "领导人"),
    ("05_1260_神圣罗马_大空位_领导人", 1260, 0, 0, 50.11, 8.68, 5, "领导人"),
    ("06_前186_西汉_吕后_领导人", -186, 0, 0, 34.26, 108.94, 4.5, "领导人"),
    ("07_1100_日本_院政_领导人", 1100, 0, 0, 35.01, 135.77, 5, "领导人"),
    ("08_1410_奥斯曼_空位期_领导人", 1410, 0, 0, 40.19, 29.06, 5, "领导人"),
    ("09_1665_清_四辅臣_领导人", 1665, 0, 0, 39.9, 116.4, 4.5, "领导人"),
    ("10_1880_清_两宫垂帘_领导人", 1880, 0, 0, 39.9, 116.4, 4.5, "领导人"),
    ("11_1290_苏格兰_护国官_领导人", 1290, 0, 0, 55.95, -3.19, 5.5, "领导人"),
    ("12_1925_匈牙利_摄政霍尔蒂_领导人", 1925, 0, 0, 47.5, 19.04, 5.5, "领导人"),
    ("13_685_唐_武则天临朝_领导人", 685, 0, 0, 34.62, 112.45, 4.5, "领导人"),
    ("14_1575_明_张居正_领导人", 1575, 0, 0, 39.9, 116.4, 4.5, "领导人"),
    # 已知问题（任务 B）
    ("20_1952_中华人民共和国_所选日期的政权", 1952, 0, 0, 39.9, 116.4, 4.5, None),
    ("21_1920_中华民国_北洋_领导人", 1920, 0, 0, 39.9, 116.4, 4.5, "领导人"),
    ("22_2020_马来西亚_首都", 2020, 6, 1, 3.14, 101.69, 6, None),
    ("23_1950_巴林", 1950, 6, 1, 26.07, 50.55, 7, None),
    ("24_1950_瑙鲁", 1950, 6, 1, -0.52, 166.93, 8, None),
    ("25_1950_科威特", 1950, 6, 1, 29.3, 47.6, 6, None),
    ("26_1950_莱恩群岛_圣诞岛", 1950, 6, 1, 1.87, -157.4, 7, None),
    ("27_1950_多米尼克", 1950, 6, 1, 15.41, -61.37, 8, None),
    ("28_1950_圣卢西亚", 1950, 6, 1, 13.9, -60.97, 8, None),
    ("29_1950_圣文森特", 1950, 6, 1, 13.25, -61.2, 8, None),
    ("30_1950_圣基茨", 1950, 6, 1, 17.3, -62.72, 8, None),
    ("31_2020_世界尺度_梵蒂冈", 2020, 6, 1, 41.9029, 12.4534, 2.5, None),
    ("32_2020_世界尺度_澳门", 2020, 6, 1, 22.19, 113.54, 2.5, None),
    ("33_1943-06-15_尼斯_意占区", 1943, 6, 15, 43.7, 7.26, 6, None),
    ("34_1939-10-15_华沙_德军军政", 1939, 10, 15, 52.23, 21.01, 5, None),
    ("35_1939-11-15_华沙_总督府", 1939, 11, 15, 52.23, 21.01, 5, None),
    # 中文名（任务 C）
    ("40_1880_新西兰_毛利_底图名称", 1880, 0, 0, -38.5, 176.0, 5, None),
    ("41_前300_盖特班_暂无通用译名", -300, 0, 0, 15.0, 46.0, 5, None),
    ("42_1650_波兰立陶宛_领导人", 1650, 0, 0, 52.23, 21.01, 5, "领导人"),
    ("43_1500_北美_底图文化名", 1500, 0, 0, 40.0, -90.0, 4, None),
    ("44_1920_北京_事件", 1920, 0, 0, 39.9, 116.4, 4.5, "事件"),
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
