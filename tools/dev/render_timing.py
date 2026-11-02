"""渲染耗时探针：跳到给定年份，记录到 hash 更新的总时间、各 API 请求耗时、404 URL。用法：render_timing.py 1900 1500 ..."""
import sys, time
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8792"
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    reqs = {}; bad = []
    pg.on("request", lambda r: reqs.__setitem__(r.url, time.time()))
    def done(r):
        t = reqs.get(r.url)
        if "/api/" in r.url and t: print(f"   {time.time()-t:6.2f}s {r.status} {r.url[len(B):][:110]}")
        if r.status >= 400: bad.append((r.status, r.url))
    pg.on("response", done)
    pg.on("requestfailed", lambda r: bad.append(("failed", r.url)))
    t0 = time.time(); pg.goto(B + "/"); pg.wait_for_load_state("networkidle"); print(f"initial {time.time()-t0:.1f}s")
    for y in sys.argv[1:]:
        y = int(y); print("==", y)
        pg.set_checked("#isBC", y < 0); pg.fill("#yearIn", str(abs(y))); pg.select_option("#monthIn", "0")
        t0 = time.time(); pg.click("#goBtn")
        for _ in range(1200):
            if pg.evaluate("location.hash.includes('date=' + WHA.dateParam() + '&') || location.hash.endsWith('date=' + WHA.dateParam())"): break
            pg.wait_for_timeout(100)
        t1 = time.time(); pg.wait_for_load_state("networkidle")
        print(f"hash {t1-t0:.1f}s  idle {time.time()-t0:.1f}s")
        for (la, lo, z) in [(48, 10, 4), (35, 105, 4), (0, 20, 3), (30, 20, 2.5)]:
            t2 = time.time()
            pg.evaluate(f"new Promise(r => {{ WHA.map.once('moveend', () => requestAnimationFrame(() => requestAnimationFrame(r))); WHA.map.setView([{la},{lo}], {z}, {{animate:false}}); }})")
            print(f"   view {la},{lo} z{z}: {time.time()-t2:.2f}s")
    print("BAD", bad)
