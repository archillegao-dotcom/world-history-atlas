#!/usr/bin/env python3
"""
回填「每日新闻」：从 1995-01-01（或 --from）到今天，写入 data/current_events/<年>.json.gz（随应用附带）。
2002-07 之后用 Portal:Current events 每日页面；之前用年份条目的 ==Events== 一节。
用法: python tools/build_current_events.py [--from 1995-01-01] [--to 2026-11-01]
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import config  # noqa: E402
from backend.live.current_events import Gazetteer, update  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--from", dest="start", default="1995-01-01")
ap.add_argument("--to", dest="end", default=dt.date.today().isoformat())
a = ap.parse_args()
gaz = Gazetteer(config.DATA_DIR / "gazetteer.json.gz")
s, e = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
# 按年分批，便于中断后续跑
for y in range(s.year, e.year + 1):
    ys, ye = max(s, dt.date(y, 1, 1)), min(e, dt.date(y, 12, 31))
    n = update([config.DATA_DIR], config.DATA_DIR, gaz, ys, ye)
    print(f"{y}: {n} items", flush=True)
