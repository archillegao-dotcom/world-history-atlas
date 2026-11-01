"""
面板模块「民生经济」：点击的区域与哪些现代国家重叠（面积比例），以及这些现代国家在所选年份的
经济与民生指标（Maddison 2023；1960 年起加世界银行 WDI），每个数值注明来源与数值所属年份，
插值/沿用最近数据时明确标注；另给主要国家的人均 GDP 与人口趋势数据（前端画小折线图）。
"""
from __future__ import annotations

from ..econ import FORMER, MEMBER_OF, MPD_CITE
from ..registry import ContentModule
from ._econ_common import store
from ._state_common import resolver

# 已解体国家：Wikidata 政权 → Maddison 整体代码
STATE_TO_FORMER = {"Q15180": "SUN", "Q36704": "YUG", "Q33946": "CSK"}


class EconPanel(ContentModule):
    id = "econ"
    title = "民生经济"
    order = 9
    description = "人均 GDP、GDP、人口、预期寿命、产业结构（按现代国家；Maddison 2023、世界银行）"
    frontend = "modules/economy.js"
    source = MPD_CITE + "；世界银行 World Development Indicators（CC BY 4.0）"

    def load(self, ctx):
        self.S = store(ctx)

    def stats(self):
        return {"countries": len(self.S.mpd)}

    def query(self, ctx, polity, date, params):
        S = self.S
        if polity is None:
            return {"items": [], "total": 0, "note": "请点击一个地区。"}
        snap, fid = params.get("snap"), polity["props"]["fid"]
        ov = S.overlap_for(ctx.basemaps, snap).get(str(fid), [])
        main = [x for x in ov if x[1] >= 0.15][:3] or ov[:1]
        y = date.y
        countries = []
        isos = [iso for iso, _ in main]
        # 已解体的国家（苏联等）：整体数值
        for c in R_strong(ctx, snap, fid, date):
            agg = STATE_TO_FORMER.get(c)
            if agg and agg not in isos:
                isos.insert(0, agg)
        share = dict(ov)
        for iso in isos:
            rows = []
            for ind, m in S.indicators.items():
                if m["src"] == "wdi" and y < 1960:
                    continue
                r = S.at(ind, iso, y)
                rows.append({"ind": ind, "zh": m["zh"], "unit": m["unit"], "src": S.source_of(ind), **(r or {"v": None})})
            countries.append({"iso": iso, "name": FORMER[iso][0] if iso in FORMER else S.name(iso),
                              "share": share.get(iso), "rows": rows,
                              "trend": {"gdppc": S.series("mpd_gdppc", iso), "pop": S.series("mpd_pop", iso),
                                        "life": S.series("wdi:SP.DYN.LE00.IN", iso) if "wdi:SP.DYN.LE00.IN" in S.indicators else []}})
        n = sum(1 for c in countries for r in c["rows"] if r["v"] is not None)
        return {"items": [], "total": n, "kind": "econ", "year": y, "overlap": ov, "countries": countries,
                "note": "经济数据按**现代国家**统计：历史时期的数值是「今天这个国家范围内」的估计，不是当时政权的数值。"
                        "这里列出与所点区域面积重叠最多的现代国家（括号内为占该区域面积的比例）。"}


def R_strong(ctx, snap, fid, date):
    try:
        return [c["state"]["id"] for c in resolver(ctx).strong(snap, fid, date)]
    except Exception:  # noqa: BLE001
        return []


MODULE = EconPanel()
