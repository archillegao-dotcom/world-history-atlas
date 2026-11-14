"""地图图层：按日期画出有来源的民国省界。不填色，不画今天的省界。"""
from __future__ import annotations

from .. import roc_admin as ROC
from ..registry import LayerModule


class RocProvincesLayer(LayerModule):
    id = "roc_provinces"
    title = "民国省界"
    order = 9
    default_on = True
    description = "1912–1949 年可再分发的中国省界。虚线只在该年有这条线时出现。没有合法数据的年份和地区不画。"
    frontend = "modules/roc_admin.js"
    source = "ENP-China / Virtual Shanghai（CC0 1.0）。同一编号的几何在各年份档里相同，按建制日期决定画不画。"

    def load(self, ctx):
        self.pack = ROC.dataset(ctx.data_dir)

    def stats(self):
        return {"records": len(self.pack["units"])}

    def layer_query(self, ctx, date, params):
        day, date_note = ROC.view_day(date)
        items = ROC.features_for(self.pack["units"], day)
        return {
            "items": items,
            "total": len(items),
            "day": day,
            "date_note": date_note,
            "license": self.pack["meta"]["source"]["license"],
            "source_url": self.pack["meta"]["source"]["url"],
            "not_implemented": self.pack["meta"].get("not_this_batch") or [],
            "note": ROC.coverage_note(self.pack["meta"]) + (date_note or ""),
        }


MODULE = RocProvincesLayer()
