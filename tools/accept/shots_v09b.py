"""
用户式截图（screenshots/v09b：v0.6.1 君主空档核对的新结果）：像用户一样在顶栏输入年份、选月/日（或不选）、点「跳转」，平移到目标位置后点击地图，必要时切换面板标签，然后截图。
同时把面板标题与正文前 300 字记入 logs/shots_v09.json，便于核对。
用法：.venv/bin/python tools/accept/shots_v08.py [名称过滤]
"""
import json, sys
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8792"
OUT = "screenshots/v09b"
LOGF = "logs/shots_v09b.json"
# 名称, 年(负=公元前), 月(0=不选), 日, 纬度, 经度, 缩放, 标签（None=默认）
S = [   # v0.6.1 君主空档核对：新补的君主（a）与新增的空位期/摄政/共治个案（b）
    ("01_1450_匈牙利_匈雅提摄政", 1450, 6, 1, 47.5, 19.04, 5.5, "领导人"),
    ("02_1600_那不勒斯_腓力三世", 1600, 6, 1, 40.85, 14.27, 5.5, "领导人"),
    ("03_1480_瑞典_老斯滕斯图雷摄政", 1480, 6, 1, 59.33, 18.07, 5, "领导人"),
    ("04_700_唐_武周", 700, 6, 1, 34.62, 112.45, 4.5, "领导人"),
    ("05_15_汉_新朝王莽", 15, 6, 1, 34.26, 108.94, 4.5, "领导人"),
    ("06_1548_莫卧儿_苏尔王朝", 1548, 6, 1, 28.61, 77.21, 5, "领导人"),
    ("07_1669_波兰_临时国王", 1669, 1, 15, 52.23, 21.01, 5, "领导人"),
    ("08_1300_苏格兰_王国守护者", 1300, 6, 1, 56.0, -3.2, 5.5, "领导人"),
    ("09_1350_匈牙利_拉约什一世", 1350, 6, 1, 47.5, 19.04, 5.5, "领导人"),
    ("10_1470_马穆鲁克_卡伊特拜", 1470, 6, 1, 30.04, 31.24, 5, "领导人"),
    ("11_1320_德里_图格鲁克", 1330, 6, 1, 28.61, 77.21, 5, "领导人"),
    ("12_1660_俄罗斯_阿列克谢", 1660, 6, 1, 55.75, 37.62, 4.5, "领导人"),
    ("13_1884_西班牙_玛丽亚克里斯蒂娜摄政", 1886, 2, 15, 40.42, -3.70, 5.5, "领导人"),
    ("14_1984_斯威士兰_王太后摄政", 1984, 6, 1, -26.32, 31.14, 7, "领导人"),
    ("15_1870_柔佛_阿布巴卡", 1870, 6, 1, 1.9, 103.5, 7, "领导人"),
    ("16_1655_爱尔兰_护国公", 1655, 6, 1, 53.35, -6.26, 6, "领导人"),
    ("17_1110_波兰_歪嘴波列斯瓦夫", 1110, 6, 1, 52.0, 19.5, 5, "领导人"),
    ("18_842_法兰克_三子内战", 842, 6, 1, 49.0, 4.0, 4.5, "领导人"),
    ("19_1965_柬埔寨_西哈努克国家元首", 1965, 6, 1, 11.56, 104.92, 6, "领导人"),
    ("20_430_萨珊_巴赫拉姆五世", 430, 6, 1, 33.1, 44.6, 4.5, "领导人"),
    ("21_1905_挪威_米歇尔森", 1905, 9, 15, 59.91, 10.75, 5, "领导人"),
    # v0.6.1 默认政权规则与马来半岛 / 日惹苏丹国区域（新功能与回归检查）
    ("22_1880_霹雳_英国驻扎官", 1880, 6, 1, 4.77, 100.94, 7, "领导人"),
    ("23_1944_雪兰莪_日占", 1944, 6, 15, 3.07, 101.52, 7, "领导人"),
    ("24_1940_日惹_苏丹位空缺", 1940, 1, 15, -7.80, 110.36, 7, "领导人"),
    ("25_850_加洛林_巴黎_回归", 850, 6, 1, 48.85, 2.35, 4.5, "领导人"),
    ("26_1880_槟城_英属马来亚_回归", 1880, 6, 1, 5.4, 100.35, 7, "领导人"),
    ("27_1350_摩洛哥_马林王朝", 1350, 6, 1, 34.03, -5.0, 5, "领导人"),
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
