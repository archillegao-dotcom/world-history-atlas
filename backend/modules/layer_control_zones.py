"""
地图图层「实际控制区」：带日期范围的次国家级控制区（如 1950 年中华民国仍控制的海南岛、舟山，1950–1961 年缅北的国民革命军残部），
数据见 data/curated/control_zones.json（每条注明日期来源与是否为近似范围），几何由 tools/build_control_zones.py 生成。
as_polity=true 的区域同时作为单独政权多边形参与点击（见 tools/build_transitions.py）；本图层只负责画轮廓与标签。
"""
from __future__ import annotations

from shapely.geometry import shape

from .. import control_zones as CZ
from ..registry import LayerModule

KIND_ZH = {"holdout": "残余控制区", "de_facto": "事实独立", "occupied": "军事占领/接管", "armed_presence": "武装存在（非主权控制）",
           "war_zone": "交战区", "leased": "租借地", "annexed": "吞并", "regime": "政权（统一/更替）",
           "unverified": "范围未核实", "claim": "声索说明，不是实际控制"}


class ControlZonesLayer(LayerModule):
    id = "control_zones"
    title = "实际控制区"
    order = 6
    description = "带日期的次国家级实际控制区（内战残余控制区、事实独立地区、武装存在等），虚线为范围，标注「大致范围」的为近似"
    frontend = "modules/control_zones.js"
    source = "data/curated/control_zones.json（日期：英文维基百科/Wikidata；几何：Natural Earth 1:10m 公有领域、historical-basemaps，或手绘近似）"

    def load(self, ctx):
        self.zones = CZ.load(ctx.data_dir)
        for z in self.zones:
            p = shape(z["geom"]).representative_point()
            z["_label"] = [round(p.x, 4), round(p.y, 4)]

    def stats(self):
        return {"records": len(self.zones)}

    def layer_query(self, ctx, date, params):
        dk = date.key()
        out = []
        for z in self.zones:
            if not CZ.active(z, dk):
                continue
            out.append({"id": z["id"], "name": z["name_zh"], "en": z.get("name_en"), "kind": z["kind"], "kind_zh": KIND_ZH.get(z["kind"], z["kind"]),
                        "controller": z["controller"], "from": z.get("from"), "until": z.get("until"), "approx": bool(z.get("approx")),
                        "dates_note": z.get("dates_note"), "note": z.get("note"), "sources": z.get("sources", []),
                        "as_polity": bool(z.get("as_polity")), "label": z["_label"], "geom": z["geom"]})
        return {"items": out, "total": len(out),
                "note": "实际控制区只覆盖已人工整理的冲突。西藏1913年起才单列；1950年10月2日以后不把整块涂成已经易手。声索样本是虚线小框，不是边界，也不改底图颜色。其他地区没有画不代表没有。只选年份、不选月份时，按这一年的年中判断。"}


MODULE = ControlZonesLayer()
