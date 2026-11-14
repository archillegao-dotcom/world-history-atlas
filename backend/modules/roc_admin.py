"""面板：所选日期的省界、名义所属和实际控制。"""
from __future__ import annotations

from .. import roc_admin as ROC
from ..registry import ContentModule


class RocAdminPanel(ContentModule):
    id = "roc_admin"
    title = "省界与实控"
    order = 40
    description = "1912–1949 年有来源的中国省界。名义所属和实际控制分开写。没有合法省界的地方标省界待考。"
    frontend = "modules/roc_admin.js"
    source = "ENP-China / Virtual Shanghai，Provinces in Republican China（CC0 1.0）。建制和实控的出处写在各条里。"

    def load(self, ctx):
        self.pack = ROC.dataset(ctx.data_dir)

    def stats(self):
        return {"records": len(self.pack["units"])}

    def query(self, ctx, polity, date, params):
        day, date_note = ROC.view_day(date)
        lat, lon = params.get("lat"), params.get("lon")
        place = ROC.place_at(self.pack, lon, lat, day)
        title = place["name"] if place["status"] == "draw" else "省界待考"
        item = {
            "id": place.get("id") or "pending",
            "title": title,
            "date": day,
            "subtitle": f"名义所属：{place['nominal']}" if place.get("nominal") else "名义所属：—",
            "desc": f"实际控制：{place['actual']}" if place.get("actual") else "实际控制：—",
            "links": [{"label": "来源", "url": url} for url in place.get("sources") or []],
            "coord": [lon, lat] if lon is not None and lat is not None else None,
        }
        return {
            "items": [item],
            "total": 1,
            "place": place,
            "date_note": date_note,
            "note": ROC.coverage_note(self.pack["meta"]),
            "license": self.pack["meta"]["source"]["license"],
            "source_url": self.pack["meta"]["source"]["url"],
        }


MODULE = RocAdminPanel()
