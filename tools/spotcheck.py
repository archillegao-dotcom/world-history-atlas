#!/usr/bin/env python3
"""人工抽查辅助：随机抽取 N 个（日期, 地图多边形），列出面板会显示的政权与元首/君主，并取英文维基百科摘要
（REST API /page/summary）供人工对照。结果写入 data/audit/spotcheck_raw.json；人工判定写在 AUDIT_REPORT.md。
用法：python tools/spotcheck.py [N=40] [seed=2026]"""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa: E402
from backend.geo import BasemapStore  # noqa: E402
from backend.polity import PolityResolver  # noqa: E402
from backend.timeutil import HDate  # noqa: E402

UA = "WorldHistoryAtlas-audit/0.5 (offline educational atlas; spot checks)"


def wiki_summary(title):
    if not title:
        return None
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        return {"title": d.get("title"), "extract": d.get("extract"), "url": d.get("content_urls", {}).get("desktop", {}).get("page")}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 2026)
    B = BasemapStore()
    R = PolityResolver(config.DATA_DIR)
    R.geo = B
    from backend.modules import leaders as L
    from backend.modules._state_common import pick_state

    class Ctx:
        shared = {"polity": R}
        basemaps = B
        data_dir = config.DATA_DIR
    out = []
    tries = 0
    while len(out) < n and tries < 5000:
        tries += 1
        # 抽样年份：古代 1/4，中世纪 1/4，近代 1/4，现代 1/4
        band = rnd.choice([(-1500, 499), (500, 1499), (1500, 1899), (1900, 2025)])
        y = rnd.randint(*band)
        if y == 0:
            continue
        d = HDate(y, rnd.randint(1, 12), rnd.randint(1, 28))
        snap = B.snapshot_at(d)
        feats = [f for f in B.features(snap).values() if f["geom"].area > 2]
        if not feats:
            continue
        f = rnd.choice(feats)
        params = {"snap": snap}
        st, alts = pick_state(Ctx, f, d, params)
        if not st:
            continue
        r = L.MODULE.query(Ctx, f, d, {"snap": snap})
        heads = [(h["role"], h["person"]["name"], h["person"].get("en")) for h in r.get("heads", [])][:2]
        offs = [(o["office"]["name"], [x["person"]["name"] for x in o["holders"]][:2]) for o in r.get("offices", [])][:3]
        rec = {"date": f"{y}-{d.m:02d}-{d.d:02d}", "snap": str(snap), "polygon": f["props"].get("NAME"),
               "state": st["id"], "state_zh": st.get("zh"), "state_en": st.get("en"), "enwiki": st.get("enwiki"),
               "life": [st.get("from"), st.get("to")], "heads": heads, "offices": offs,
               "alts": [(a["name"], a["method"]) for a in alts[:4]]}
        rec["wiki"] = wiki_summary(st.get("enwiki"))
        out.append(rec)
        time.sleep(0.3)
    p = config.DATA_DIR / "audit" / "spotcheck_raw.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("wrote", p, len(out))


if __name__ == "__main__":
    main()
