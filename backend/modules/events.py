"""
模块「事件」：Wikidata 中有时间点(P585)或开始时间(P580)的历史事件。
查询逻辑：
  1. 时间过滤：所选日期 ± span 年内开始的事件，以及所选日期正在进行中（开始≤日期≤结束）的事件；
  2. 空间过滤：事件的任一候选坐标（自身 P625、地点 P276、参与方 P710 的坐标/首都、国家 P17 的坐标）
     落在所点击政权的多边形内；完全没有坐标时按「国家 P17」名称与政权名称匹配；
  3. 排序：同一天 > 距离所选日期越近 > sitelinks（维基语言版本数，衡量知名度）越高。
"""
from __future__ import annotations

from pathlib import Path

from ..registry import ContentModule
from ..timeutil import rec_key
from ._common import fmt_time, links, load_country_names, load_records, match_any


# 有日期但不是「事件」的 Wikidata 类型（年份条目、某年某国概览、货币、道路……），加载时过滤。
# 构建脚本 tools/build_wikidata.py 的 NON_EVENT_TYPES 已过滤大部分，这里是第二道防线。
EXCLUDE_TYPES = {
    "Q18340514",  # events in a specific year or time period（如「1789年法国」）
    "Q3186692", "Q577", "Q19828", "Q39911", "Q14795564", "Q16929628",  # 年份/十年/闰年/共和历年
    "Q235670", "Q235673", "Q235676", "Q235680", "Q235684", "Q235687", "Q235690",  # common year starting on …
    "Q217041", "Q217024", "Q217036", "Q217026", "Q217034", "Q217015", "Q217033",  # leap year starting on …
    "Q8142", "Q28783456", "Q113813711", "Q1426271",  # 货币、硬币类型、国道
}


class EventsModule(ContentModule):
    id = "events"
    title = "事件"
    order = 10
    description = "该时间前后在此政权范围内发生的历史事件（来自 Wikidata）"
    source = "Wikidata（P585 时间点 / P580 开始时间，CC0）"

    def load(self, ctx):
        self.recs = load_records(Path(ctx.data_dir) / "events.json.gz")
        for r in self.recs:
            r["_k"] = rec_key(r.get("start"))
            r["_e"] = rec_key(r.get("end"))
        self.recs = [r for r in self.recs if r["_k"] is not None and not (set(r.get("types", [])) & EXCLUDE_TYPES)]
        self.recs.sort(key=lambda r: r["_k"])
        self.countries = load_country_names(ctx)

    def stats(self):
        return {"records": len(self.recs)}

    def query(self, ctx, polity, date, params):
        dk = date.key()
        # 默认窗口：年代越早，数据越稀疏，窗口越大
        span = float(params.get("span") or (2 if date.y >= 1500 else 10 if date.y >= 0 else 50 if date.y >= -1000
                                            else 150 if date.y >= -3000 else 2000))
        limit = int(params.get("limit") or 80)
        out = []
        for r in self.recs:
            if r["_k"] > dk + span:
                break
            ongoing = r["_e"] is not None and r["_k"] <= dk <= r["_e"]
            if not (abs(r["_k"] - dk) <= span or ongoing):
                continue
            # 持续数百年的「时代/称号」类条目只在知名度很高时显示，避免淹没具体事件
            if ongoing and r["_e"] - r["_k"] > 150 and r.get("sl", 0) < 60:
                continue
            how = match_any(r, polity, self.countries)
            if not how:
                continue
            st = r["start"]
            same_day = bool(date.d) and st["y"] == date.y and st.get("m") == date.m and st.get("d") == date.d
            same_month = bool(date.m) and st["y"] == date.y and st.get("m") == date.m
            ydist = abs(st["y"] - date.y)
            # 排序：当天 > 当月 > 同一年开始 > 正在进行 > 距离（年）越近；同组内 sitelinks（知名度）高的在前
            bucket = 0 if same_day else 1 if same_month else 2 if ydist == 0 else 3 if ongoing else 4 + ydist
            out.append({
                "id": r["id"], "title": r.get("name") or r.get("en_name") or r["id"], "title_en": r.get("en_name"),
                "date": fmt_time(r["start"]) + (f" — {fmt_time(r['end'])}" if r.get("end") else ""),
                "subtitle": ("★ 当天 " if same_day else "进行中 " if ongoing and ydist else "") + (r.get("desc") or ""),
                "coord": r.get("coord"), "match": how, "coord_src": r.get("coord_src"),
                "links": links(r), "score": r.get("sl", 0),
                "_sort": (bucket, -r.get("sl", 0)),
            })
        out.sort(key=lambda x: x.pop("_sort"))
        total = len(out)
        return {"items": out[:limit], "total": total, "note": f"时间窗口：所选日期前后 {span:g} 年，以及当时正在进行中的事件"}


MODULE = EventsModule()
