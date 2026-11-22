"""地图图层：欧洲和中国以外、有起止日期的历史区划。不填色。"""
from __future__ import annotations

from .. import hist_admin as HA
from ..registry import LayerModule


class HistAdminLayer(LayerModule):
    id = "hist_div"
    title = "历史区划"
    order = 10
    default_on = True
    description = "欧洲、中国以外，所选日期当天有起止日期的区划和殖民地界。虚线不填色。没有合法几何的不画，标待考。"
    frontend = "modules/hist_admin.js"
    source = "OpenHistoricalMap（CC0 1.0）。只收同时有 start_date 和 end_date 的关系。"

    def load(self, ctx):
        self.pack = HA.dataset(ctx.data_dir)

    def stats(self):
        return {"records": len(self.pack["features"])}

    def layer_query(self, ctx, date, params):
        day, date_note = HA.view_day(date)
        items = HA.features_for(self.pack, day)
        return {
            "items": items,
            "total": len(items),
            "day": day,
            "date_note": date_note,
            "counts": HA.counts_for(self.pack, day),
            "license": self.pack["pending"]["license"],
            "source_url": self.pack["pending"]["license_url"],
            "note": self.pack["pending"]["rule"] + (date_note or ""),
            "gaps": self.pack["pending"]["gaps"],
        }


MODULE = HistAdminLayer()
