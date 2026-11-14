"""地图图层：实际控制、主权声索、国际承认分开。

实控填色只画这一层自己有轮廓、并且没有交给战争前线的区域。
克里米亚、顿巴斯和 2022 年后的评估控制仍用战争前线的填色，这里不另铺一层。
声索用虚线，不改策略地图的陆地配色。
"""
from __future__ import annotations

from .. import status_layers as SL
from ..registry import LayerModule


class StatusLayersLayer(LayerModule):
    id = "status_layers"
    title = "实控 / 声索 / 承认"
    order = 8
    default_on = True
    description = "把实际控制、主权声索和国际承认分成三行。实控沿用战争前线或单独填色，声索是虚线，不改策略地图配色。"
    frontend = "modules/status_layers.js"
    source = "data/curated/status_layers.json；轮廓为 Natural Earth 1:10m 公有领域行政界，或已有的战争前线"

    def load(self, ctx):
        self.areas = SL.load(ctx.data_dir)

    def stats(self):
        return {"records": sum(len(a.get("statements") or []) for a in self.areas), "areas": len(self.areas)}

    def layer_query(self, ctx, date, params):
        params = params or {}
        lon = _f(params.get("lon"))
        lat = _f(params.get("lat"))
        rows_only = str(params.get("rows") or "") == "1"
        out = {
            "items": [] if rows_only else SL.features_for(self.areas, date),
            "hits": SL.hit(self.areas, date, lon, lat) if lon is not None and lat is not None else [],
            "note": "实际控制、主权声索、国际承认分开写。虚线是声索或宣布的范围，不是控制线。没有几何的标待考，不画。战争前线已经画出的评估控制，这里不另铺一层颜色。",
        }
        want = params.get("area")
        if want:
            area = next((a for a in self.areas if a.get("id") == want), None)
            out["area"] = None if area is None else {
                "id": area["id"],
                "name_zh": area.get("name_zh"),
                "precision_zh": area.get("precision_zh"),
                "probe": (area.get("_geom") or {}).get("probe"),
                "rows": SL.rows_for(area, date, lon, lat),
            }
        out["total"] = len(out["items"])
        return out


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


MODULE = StatusLayersLayer()
