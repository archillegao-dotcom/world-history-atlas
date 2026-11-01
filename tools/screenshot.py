#!/usr/bin/env python3
"""用无头浏览器 (Playwright Chromium) 截图。用法:
  python tools/screenshot.py http://127.0.0.1:8790 "#date=1789-07-14&name=France&tab=events" out.png [宽 高]
"""
import sys
from playwright.sync_api import sync_playwright

base, frag, out = sys.argv[1], sys.argv[2], sys.argv[3]
w, h = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1440, 900)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    pg.goto(base + "/" + frag)
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=out)
    b.close()
print("saved", out)
