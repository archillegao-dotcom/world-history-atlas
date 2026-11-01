"""
后台自动更新调度器：应用运行期间，每隔 WHA_UPDATE_MINUTES 分钟（默认 60）抓取最近几天的
维基百科每日新闻页面（当天的页面一天中会不断补充，所以总是重抓最近 3 天），
如果上次更新距今较久（例如电脑关机一周），会补抓缺失的日期（单次最多 400 天）。
没有网络时静默失败，下次再试；设置 WHA_AUTO_UPDATE=0 可关闭。
"""
from __future__ import annotations

import datetime as dt
import json
import threading
import time
import traceback

from .. import config
from .current_events import Gazetteer, load_year, update

STATUS = {"enabled": config.AUTO_UPDATE, "interval_minutes": config.UPDATE_MINUTES, "running": False,
          "last_check": None, "last_day": None, "error": None, "last_added": 0}
_STATE_FILE = config.USER_DATA_DIR / "update_state.json"


def _last_day() -> dt.date | None:
    today = dt.date.today()
    for y in range(today.year, 1994, -1):
        days = load_year([config.DATA_DIR, config.USER_DATA_DIR], y)
        if days:
            return dt.date.fromisoformat(max(days))
    return None


def run_once(on_update=None, log=print) -> int:
    STATUS["running"] = True
    try:
        today = dt.datetime.now(dt.timezone.utc).date()
        last = _last_day()
        start = today - dt.timedelta(days=2)
        if last and last < start:
            start = max(last - dt.timedelta(days=1), today - dt.timedelta(days=400))
        gaz = Gazetteer(config.DATA_DIR / "gazetteer.json.gz")
        n = update([config.DATA_DIR, config.USER_DATA_DIR], config.USER_DATA_DIR, gaz, start, today, log=log)
        STATUS.update(last_added=n, error=None)
        if on_update:
            on_update(sorted({start.year, today.year}))
        return n
    except Exception as e:  # 网络等错误：记录后下次再试
        STATUS["error"] = f"{type(e).__name__}: {e}"
        log("current events update failed: " + "".join(traceback.format_exception_only(type(e), e)).strip())
        return 0
    finally:
        STATUS["running"] = False
        STATUS["last_check"] = dt.datetime.now().isoformat(timespec="seconds")
        d = _last_day()
        STATUS["last_day"] = d.isoformat() if d else None
        try:
            config.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            _STATE_FILE.write_text(json.dumps(STATUS, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def start(on_update=None) -> None:
    d = _last_day()
    STATUS["last_day"] = d.isoformat() if d else None
    if not config.AUTO_UPDATE:
        return

    def loop():
        time.sleep(5)  # 让服务先启动
        while True:
            run_once(on_update, log=lambda m: print(m, flush=True))
            time.sleep(config.UPDATE_MINUTES * 60)

    threading.Thread(target=loop, name="current-events-updater", daemon=True).start()
