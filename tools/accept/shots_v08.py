"""
用户式截图（screenshots/v08）：像用户一样在顶栏输入年份、选月/日（或不选）、点「跳转」，平移到目标位置后点击地图，必要时切换面板标签，然后截图。
同时把面板标题与正文前 300 字记入 logs/shots_v08.json，便于核对。
用法：.venv/bin/python tools/accept/shots_v08.py [名称过滤]
"""
import json, sys
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8792"
OUT = "screenshots/v08"
# 名称, 年(负=公元前), 月(0=不选), 日, 纬度, 经度, 缩放, 标签（None=默认）
S = [
    ("01_1942-12-24_欧洲_斯大林格勒", 1942, 12, 24, 48.71, 44.51, 4.5, None),
    ("02_1942-12-24_欧洲_维希法国", 1942, 12, 24, 45.78, 3.08, 4.5, None),
    ("03_1939-10-15_波兰_华沙", 1939, 10, 15, 52.23, 21.01, 5, None),
    ("04_1940-07-15_法国_非占领区", 1940, 7, 15, 46.13, 3.43, 5, None),
    ("05_1944-07-15_欧洲_东线", 1944, 7, 15, 53.9, 27.56, 4.5, None),
    ("06_1945-06-15_柏林_苏占区", 1945, 6, 15, 52.52, 13.41, 5, None),
    ("10_1932-06-15_中国_满洲国", 1932, 6, 15, 43.88, 125.32, 4.5, None),
    ("11_1938-12-15_中国_南京维新政府", 1938, 12, 15, 32.06, 118.8, 4.5, None),
    ("12_1941-12-15_中国_汪政权", 1941, 12, 15, 32.06, 118.8, 4.5, None),
    ("13_1944-12-15_中国_桂林日占", 1944, 12, 15, 25.27, 110.29, 4.5, None),
    ("14_1945-09-15_中国_沈阳苏军", 1945, 9, 15, 41.8, 123.43, 4.5, None),
    ("20_1950只选年份_北京", 1950, 0, 0, 39.9, 116.4, 4.5, None),
    ("21_1950只选年份_台北", 1950, 0, 0, 25.03, 121.56, 5, None),
    ("22_1952只选年份_东北哈尔滨", 1952, 0, 0, 45.75, 126.65, 4.5, None),
    ("23_1947-06-01_东北哈尔滨共军控制区", 1947, 6, 1, 45.75, 126.65, 4.5, None),
    ("30_1992-01-01_前苏联_基辅", 1992, 1, 1, 50.45, 30.52, 3.5, None),
    ("31_1992-01-01_前苏联_阿拉木图", 1992, 1, 1, 43.24, 76.89, 3.5, None),
    ("40_1950-06-01_新加坡殖民地", 1950, 6, 1, 1.35, 103.82, 6, None),
    ("41_1964-06-01_新加坡属马来西亚", 1964, 6, 1, 1.35, 103.82, 6, None),
    ("42_1966-06-01_新加坡独立", 1966, 6, 1, 1.35, 103.82, 6, None),
    ("50_公元1年_西汉_领导人", 1, 0, 0, 34.26, 108.94, 4, "领导人"),
    ("51_220年_东汉曹魏_领导人", 220, 0, 0, 34.62, 112.45, 4, "领导人"),
    ("52_1100年_北宋_领导人", 1100, 0, 0, 34.8, 114.3, 4, "领导人"),
    ("53_1700年_清_领导人", 1700, 0, 0, 39.9, 116.4, 4, "领导人"),
    ("54_前204年_西楚_领导人", -204, 0, 0, 34.62, 112.45, 4, "领导人"),
    ("60_2020-06-01_法国面板_第五共和国", 2020, 6, 1, 46.6, 2.4, 5, None),
    ("61_1942-06-01_法国面板_维希", 1942, 6, 1, 46.13, 3.43, 5, "政权性质"),
    ("62_1920-06-01_中华民国_五色旗", 1920, 6, 1, 32.06, 118.8, 4.5, "政权性质"),
    ("63_1935-06-01_中华民国_青天白日满地红", 1935, 6, 1, 30.6, 114.3, 4.5, "政权性质"),
    ("64_2020-06-01_台湾_中华民国国旗", 2020, 6, 1, 23.7, 121.0, 6, "政权性质"),
    ("70_2022-02-24_俄乌战线", 2022, 2, 24, 48.5, 35.0, 5.5, None),
    ("71_2022-03-15_俄乌战线", 2022, 3, 15, 48.5, 35.0, 5.5, None),
    ("72_2022-11-15_俄乌战线_赫尔松收复", 2022, 11, 15, 47.0, 34.0, 5.5, None),
    ("73_2022-12-31_俄乌战线", 2022, 12, 31, 48.5, 35.0, 5.5, None),
    ("74_2026-11-01_俄乌战线", 2026, 11, 1, 48.5, 35.0, 5.5, None),
    ("80_1990-10-01_科威特_伊拉克占领", 1990, 10, 1, 29.37, 47.98, 6, None),
    ("81_1938-07-01_亚的斯亚贝巴_意属东非", 1938, 7, 1, 9.03, 38.74, 5, None),
    ("90_1999-12-01_澳门_葡萄牙管治", 1999, 12, 1, 22.19, 113.54, 9, None),
    ("91_2000-06-01_澳门_特别行政区", 2000, 6, 1, 22.19, 113.54, 9, None),
    ("92_2020-06-01_波兰面板", 2020, 6, 1, 52.0, 19.4, 5, None),
    ("93_1949-05-01_南京_共军控制区", 1949, 5, 1, 32.06, 118.8, 5, None),
    ("94_1990-06-01_北塞浦路斯", 1990, 6, 1, 35.25, 33.5, 7, None),
]
flt = sys.argv[1] if len(sys.argv) > 1 else None
log = []
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
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
json.dump({"shots": log, "console_errors": errs[:20]}, open("logs/shots_v08.json", "w"), ensure_ascii=False, indent=1)
print("console errors:", len(errs))
