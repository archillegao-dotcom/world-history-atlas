"""面板：点到的历史区划，或该地区的待考说明。"""
from __future__ import annotations

from .. import hist_admin as HA
from ..registry import ContentModule


class HistAdminPanel(ContentModule):
    id = "hist_div_panel"
    title = "区划"
    order = 41
    description = "欧洲和中国以外的历史区划。有 CC0 几何才写名称和日期。没有的标区划待考。"
    frontend = "modules/hist_admin.js"
    source = "OpenHistoricalMap（CC0 1.0）"

    def load(self, ctx):
        self.pack = HA.dataset(ctx.data_dir)

    def stats(self):
        return {"records": len(self.pack["features"])}

    def query(self, ctx, polity, date, params):
        day, date_note = HA.view_day(date)
        place = HA.place_at(self.pack, params.get("lon"), params.get("lat"), day)
        title = place["name"] if place.get("status") == "draw" else "区划待考"
        return {
            "items": [{
                "id": place.get("id") or "pending",
                "title": title,
                "date": day,
                "subtitle": place.get("kind") or "",
                "desc": place.get("note") or "",
                "links": [{"label": "来源", "url": place["source_url"]}] if place.get("source_url") else [],
            }],
            "total": 1,
            "place": place,
            "day": day,
            "date_note": date_note,
            "counts": HA.counts_for(self.pack, day),
            "license": self.pack["pending"]["license"],
            "source_url": self.pack["pending"]["license_url"],
            "note": self.pack["pending"]["rule"],
            "gaps": self.pack["pending"]["gaps"],
        }


MODULE = HistAdminPanel()
