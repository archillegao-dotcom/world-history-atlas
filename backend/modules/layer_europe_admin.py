"""地图图层：按日期画出有来源的欧洲一级行政区。不填色，不画今天的省界。"""
from __future__ import annotations

from .. import europe_admin as EU
from .. import roc_admin as ROC
from ..registry import LayerModule


class EuropeAdminLayer(LayerModule):
    id = "europe_admin"
    title = "欧洲历史省界"
    order = 10
    default_on = True
    description = "有再分发许可的欧洲一级行政区，按所选日期画虚线。没有合法几何的地方不画。"
    frontend = "modules/europe_admin.js"
    source = "HistoGIS、TRF-GIS、ISTAT、1897年俄国普查、波兰第二共和国、英国传统郡。许可写在各条。"

    def load(self, ctx):
        self.pack = EU.dataset(ctx.data_dir)

    def stats(self):
        return {"records": len(self.pack["units"])}

    def layer_query(self, ctx, date, params):
        day, date_note = ROC.view_day(date)
        items = EU.features_for(self.pack["units"], day)
        return {
            "items": items,
            "total": len(items),
            "day": day,
            "date_note": date_note,
            "license": "见各条",
            "note": EU.coverage_note(self.pack) + (date_note or ""),
            "gaps": self.pack.get("gaps") or [],
        }


MODULE = EuropeAdminLayer()
