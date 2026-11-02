"""像用户一样点击地图：python tools/dev/click_probe.py BASE 'date,lat,lon,zoom[,shot.png]' ..."""
import sys, json
from playwright.sync_api import sync_playwright
base = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    for arg in sys.argv[2:]:
        a = arg.split(","); date, lat, lon, z = a[0], float(a[1]), float(a[2]), float(a[3])
        pg.goto(f"{base}/#date={date}&c={lat},{lon}&z={z}"); pg.reload()
        pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
        pt = pg.evaluate(f"(() => {{ const q = WHA.map.latLngToContainerPoint([{lat},{lon}]); const r = document.getElementById('map').getBoundingClientRect(); return [q.x + r.left, q.y + r.top]; }})()")
        top = pg.evaluate(f"(() => {{ const e = document.elementFromPoint({pt[0]},{pt[1]}); return e ? (e.tagName + '.' + (e.className.baseVal ?? e.className) + '#' + e.id) : null; }})()")
        pg.mouse.click(*pt); pg.wait_for_timeout(2500)
        vis = pg.evaluate("!document.getElementById('panel').classList.contains('hidden')")
        name = pg.inner_text("#polityName") if vis else None
        reg = pg.evaluate("(() => { const b = document.querySelector('#tabBody'); return b ? b.innerText.slice(0, 200) : null; })()") if vis else None
        print(json.dumps({"q": arg, "hit": top, "panel": vis, "name": name, "body": reg}, ensure_ascii=False))
        if len(a) > 4: pg.screenshot(path=a[4])
    if errs: print("console errors:", errs[:5])
    b.close()
