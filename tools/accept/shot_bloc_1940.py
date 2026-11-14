"""阵营地图截图：1940-11-02 欧洲，勾选轴心国+同盟国，并点击巴黎（德占法国）读面板。"""
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8792"
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(B + "/#date=1940-11-02&layers=alliances,zones&blocs=Q43056,Q329888")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(8000)
    pg.evaluate("WHA.map.setView([48,12], 4, {animate:false})")
    pg.wait_for_timeout(15000); pg.wait_for_load_state("networkidle")
    pg.mouse.move(5, 300); pg.wait_for_timeout(500)
    pg.screenshot(path="screenshots/v10_roc/17_1940-11_欧洲_阵营地图.png")
    print(pg.inner_text(".alliance-legend")[:300])
    br.close()
