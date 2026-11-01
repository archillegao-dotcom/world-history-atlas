"""
地图图层「经济与资源」中的经济分级设色（choropleth）：按所选年份给**现代国界**着色。

Maddison / 世界银行的数据都是按现代国家统计的，所以这一图层画的是 Natural Earth 现代国界（不是当时的边界），
历史边界以细线叠在上面，便于对照。插值、沿用最近数据的国家在返回值里有标记，前端以虚线边框显示。
分级：按当年有数据国家的分位数（7 级）。
"""
from __future__ import annotations

from ..econ import MPD_CITE
from ..registry import LayerModule
from ._econ_common import store


class EconomyLayer(LayerModule):
    id = "economy"
    title = "经济"
    order = 7
    default_on = False
    description = "按现代国界的人均 GDP / GDP / 人口 / 预期寿命 / 产业结构等（Maddison 2023、世界银行）"
    frontend = "modules/economy.js"
    source = MPD_CITE + "；世界银行 World Development Indicators（CC BY 4.0）"

    def load(self, ctx):
        self.S = store(ctx)

    def stats(self):
        return {"maddison_countries": len(self.S.mpd), "wdi_indicators": len(self.S.wdi)}

    def layer_query(self, ctx, date, params):
        S = self.S
        ind = params.get("ind") or "mpd_gdppc"
        if ind not in S.indicators:
            ind = "mpd_gdppc"
        y = date.y
        isos = sorted(set(S.ne_iso.values()))
        vals = {}
        for iso in isos:
            r = S.at(ind, iso, y)
            if r:
                vals[iso] = r
        xs = sorted(r["v"] for r in vals.values())
        breaks = [xs[int(len(xs) * k / 7)] for k in range(1, 7)] if len(xs) >= 7 else xs
        snap = ctx.basemaps.snapshot_for(y)
        return {"indicator": ind, "meta": S.indicators[ind], "source": S.source_of(ind),
                "indicators": [{"id": k, "zh": m["zh"]} for k, m in S.indicators.items()],
                "values": vals, "breaks": breaks, "ne_iso": S.ne_iso,
                "overlap": S.overlap.get(str(snap), {}) if snap != 2011 else {k: [[v, 1.0]] for k, v in S.ne_iso.items()},
                "names": {iso: S.name(iso) for iso in vals}, "snapshot": snap, "total": len(vals),
                "note": "数值按现代国界统计（历史时期为「今天这一范围」的估计）。虚线边框 = 插值或沿用最近数据。"}


MODULE = EconomyLayer()
