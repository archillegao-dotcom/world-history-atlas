"""
模块「每日新闻」：英文维基百科 Portal:Current events 每日页面（2002 年中至今），
以及 1995–2002 年的年份条目（==Events== 一节）。数据随应用附带（data/current_events/），
并由后台调度器（backend/live/scheduler.py）每隔一段时间自动抓取最近几天，写入用户数据目录。

查询：所选日期精确到日 → 当天的条目；只到月 → 当月；只到年 → 当年（按日期排序，取前 N 条）。
归属：条目中链接到的地点（国家/城市/行政区，经本地地名表定位）任一落在所点击政权范围内即显示。
文字为英文原文（中文维基没有对应的每日页面），地点名称显示中文。
"""
from __future__ import annotations

import datetime as dt
import threading

from shapely.geometry import Point

from .. import config
from ..live.current_events import load_year, page_url_for
from ..registry import ContentModule

FIRST_YEAR = 1995


class NewsModule(ContentModule):
    id = "news"
    title = "每日新闻"
    order = 12
    description = "维基百科「时事」每日新闻（1995 年至今，每天自动更新）"
    source = "English Wikipedia — Portal:Current events（每日页面）及年份条目，CC BY-SA 4.0"

    def load(self, ctx):
        self.dirs = [config.DATA_DIR, config.USER_DATA_DIR]
        self.cache: dict[int, dict] = {}
        self.lock = threading.Lock()

    def invalidate(self, years=None):
        """调度器写入新数据后调用，丢弃对应年份的内存缓存。"""
        with self.lock:
            for y in (years or list(self.cache)):
                self.cache.pop(y, None)

    def year(self, y: int) -> dict:
        with self.lock:
            if y not in self.cache:
                self.cache[y] = load_year(self.dirs, y)
            return self.cache[y]

    def stats(self):
        n, days = 0, 0
        for y in range(FIRST_YEAR, dt.date.today().year + 1):
            d = self.year(y)
            days += len(d)
            n += sum(len(v) for v in d.values())
        return {"records": n, "days": days}

    def query(self, ctx, polity, date, params):
        if date.y < FIRST_YEAR:
            return {"items": [], "total": 0, "note": f"每日新闻数据从 {FIRST_YEAR} 年开始；更早的历史请看「事件」标签。"}
        limit = int(params.get("limit") or 120)
        days = self.year(date.y)
        if date.m and date.d:
            keys = [f"{date.y:04d}-{date.m:02d}-{date.d:02d}"]
            scope = "当天"
        elif date.m:
            keys = sorted(k for k in days if k.startswith(f"{date.y:04d}-{date.m:02d}-"))
            scope = "当月"
        else:
            keys = sorted(days)
            scope = "当年"
        out = []
        for k in keys:
            for it in days.get(k, []):
                places = it.get("places", [])  # [[lon, lat, 名称, 是否国家]]
                if polity is not None:
                    if not any(polity["geom"].contains(Point(p[0], p[1])) for p in places):
                        continue
                tags = [p[2] for p in places[:4]]
                links = [{"label": "维基百科当日页面", "url": page_url_for(k)}]
                links += [{"label": "来源：" + s[1], "url": s[0]} for s in it.get("sources", [])[:3]]
                out.append({
                    "id": it["id"], "title": it["text"], "title_en": None, "date": k,
                    "subtitle": " · ".join(x for x in [
                        ("话题：" + " › ".join(it["context"][-2:])) if it.get("context") else "",
                        ("类别：" + it["cat"]) if it.get("cat") else "",
                        ("地点：" + "、".join(tags)) if tags else "未能定位"] if x),
                    "coord": [places[0][0], places[0][1]] if places else None,
                    "match": "coord" if polity is not None else "world", "links": links, "score": 0,
                })
        total = len(out)
        missing = not days.get(keys[0]) if scope == "当天" else not keys
        note = f"{scope}的维基百科时事条目（英文原文）"
        if missing:
            note += "。这一天暂无数据（可能还未更新，或当天页面不存在）"
        return {"items": out[:limit], "total": total, "note": note}


MODULE = NewsModule()
