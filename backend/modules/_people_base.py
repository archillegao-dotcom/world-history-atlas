"""
人物类模块的通用实现：显示所选日期「在世」的某职业人物。
- 在世判断：出生 ≤ 日期 ≤ 去世；无去世日期时，假定寿命不超过 100 年；
- 所属政权：出生地坐标(P19→P625)落在该政权多边形内（注意：这是出生地，人物后来可能迁居），
  无出生地坐标时按国籍(P27)名称与政权名称匹配；
- 排序：先按「描述是否提到该职业」（Wikidata 的职业 P106 往往很宽泛，例如化学家拉瓦锡也被标为 writer，
  描述里写明“作家/诗人”的人更可能以此著称），再按 sitelinks（维基语言版本数）降序。
  被降级的人仍会显示，只是排在后面——不删除、不改写任何数据。
新增一个人物类别只需在 backend/modules/ 新建文件：
    from ._people_base import PeopleModule
    MODULE = PeopleModule("people_painter", "画家", "people_painter.json.gz", order=50)
并在 tools/build_wikidata.py 的 PEOPLE_CATEGORIES 里加上对应职业 QID 后重新抓取数据。
"""
from __future__ import annotations

from pathlib import Path

from ..registry import ContentModule
from ..timeutil import rec_key
from ._common import fmt_time, links, load_country_names, load_records, matches_polity


class PeopleModule(ContentModule):
    source = "Wikidata（P106 职业、P569/P570 生卒、P19 出生地、P27 国籍，CC0）"

    def __init__(self, id: str, title: str, data_file: str, order: int = 50, description: str = "",
                 keywords: tuple[str, ...] = ()):
        self.id, self.title, self.data_file, self.order = id, title, data_file, order
        self.keywords = tuple(k.lower() for k in keywords)
        self.description = description or f"该日期在世、出生于此政权范围内的{title}（按知名度排序）"

    def load(self, ctx):
        self.recs = []
        for r in load_records(Path(ctx.data_dir) / self.data_file):
            b = rec_key(r.get("birth"))
            if b is None:
                continue
            r["_b"] = b
            r["_d"] = rec_key(r.get("death"))
            self.recs.append(r)
        self.countries = load_country_names(ctx)

    def stats(self):
        return {"records": len(self.recs)}

    def query(self, ctx, polity, date, params):
        dk = date.key()
        limit = int(params.get("limit") or 60)
        out = []
        for r in self.recs:  # 已按 sitelinks 降序
            end = r["_d"] if r["_d"] is not None else r["_b"] + 100
            if not (r["_b"] <= dk <= end):
                continue
            how = matches_polity(r, polity, self.countries)
            if not how:
                continue
            age = int(dk - r["_b"])
            desc = (r.get("desc") or "").lower()
            primary = not self.keywords or any(k in desc for k in self.keywords)
            out.append({
                "id": r["id"], "title": r.get("name") or r.get("en_name") or r["id"], "title_en": r.get("en_name"),
                "date": f"{fmt_time(r['birth'])} — {fmt_time(r.get('death')) if r.get('death') else '?'}",
                "subtitle": f"当时约 {age} 岁" + (f" · {r['desc']}" if r.get("desc") else ""),
                "coord": r.get("coord"), "match": how, "links": links(r), "score": r.get("sl", 0),
                "_p": 0 if primary else 1,
            })
        out.sort(key=lambda x: x.pop("_p"))  # 稳定排序：同组内保持 sitelinks 降序
        return {"items": out[:limit], "total": len(out),
                "note": "按出生地坐标落在该政权范围内判断（无坐标时按国籍）；人物可能后来生活在别处"}
