"""面板：所选日期的省界、名义所属和实际控制。"""
from __future__ import annotations

from .. import europe_admin as EU
from .. import roc_admin as ROC
from .. import roc_beiyang as BY
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
        europe = False
        if place["status"] == "none" and lon is not None and lat is not None:
            eu = EU.place_at(EU.dataset(ctx.data_dir), lon, lat, day)
            if eu["status"] == "draw":
                place = eu
                europe = True
        local = {"wars": [], "fronts": [], "seats": [], "county_license": "", "county_url": ""}
        if not europe:
            local = BY.for_province(ctx.data_dir, day, place.get("id"))
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
        if europe:
            note = "这一层是有来源的欧洲一级行政区。没有几何的地方仍标省界待考。不画今天的省界。"
            license_name = place.get("license") or ""
            source_url = (place.get("sources") or [None])[0]
        else:
            note = ROC.coverage_note(self.pack["meta"])
            license_name = self.pack["meta"]["source"]["license"]
            source_url = self.pack["meta"]["source"]["url"]
        return {
            "items": [item],
            "total": 1,
            "place": place,
            "date_note": date_note,
            "note": note,
            "license": license_name,
            "source_url": source_url,
            "europe": europe,
            "wars": local["wars"],
            "fronts": local["fronts"],
            "seats": local["seats"],
            "county_license": local["county_license"],
            "county_url": local["county_url"],
        }


MODULE = RocAdminPanel()
