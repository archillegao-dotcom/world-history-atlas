"""
地图图层「资源」：Wikidata 中有坐标的矿山、油田、天然气田（≥2 个语言版本的维基条目，data/resources.json.gz）。
时间：有开始时间（P571/P580）的，从开始到关闭（P576/P582）显示；**没有开始时间的只在 2000 年以后显示**，
并标注「开采时间未记录」（这些条目通常描述的是现代仍在运营或近代的矿区，不能放到更早的年代）。
"""
from __future__ import annotations

from pathlib import Path

from ..registry import LayerModule
from ..timeutil import rec_key
from ._common import fmt_time, load_records

KIND_ZH = {"mine": "矿山", "oil": "油田", "gas": "天然气田"}


class ResourcesLayer(LayerModule):
    id = "resources"
    title = "资源"
    order = 8
    default_on = False
    description = "矿山、油田、天然气田（Wikidata，有坐标与年代的）"
    frontend = "modules/economy.js"
    source = "Wikidata（mine Q820477、oil field Q211748、natural gas field Q1349255 及子类；P625 坐标、P571/P576 年代、P1056 产品，CC0）"

    def load(self, ctx):
        self.recs = load_records(Path(ctx.data_dir) / "resources.json.gz")

    def stats(self):
        return {"records": len(self.recs), "dated": sum(1 for r in self.recs if r.get("from"))}

    def layer_query(self, ctx, date, params):
        dk = date.key()
        out = []
        for r in self.recs:
            a, b = rec_key(r.get("from")), rec_key(r.get("to"))
            if a is None:
                if date.y < 2000 or (b is not None and dk > b):
                    continue
            elif a > dk or (b is not None and dk > b + 1):
                continue
            out.append({"id": r["id"], "c": r["coord"], "k": r["kind"], "n": r.get("zh") or r.get("en"),
                        "p": (r.get("products") or [])[:4], "f": fmt_time(r.get("from")) if r.get("from") else None,
                        "t": fmt_time(r.get("to")) if r.get("to") else None, "zw": r.get("zhwiki"), "ew": r.get("enwiki")})
        return {"items": out, "total": len(out), "kinds": KIND_ZH,
                "note": "没有开始时间的资源点只在 2000 年以后显示。"}


MODULE = ResourcesLayer()
