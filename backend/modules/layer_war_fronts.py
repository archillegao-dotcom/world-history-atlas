"""
地图图层「战争前线」：逐日的占领区 / 灰色区（交战双方实际控制范围）。
数据格式与「实际控制区」相同（id/group/kind/controller/from/until/geometry/approx/sources，见 data/curated/control_zones.json 的 _doc），
另加 dataset / snapshot / area_km2；几何按快照存放在 data/war_fronts/<war>/<snapshot>.json.gz，由各战争的构建脚本生成：
  俄乌战争：tools/build_war_fronts_ukraine.py（ISW/CTP 2022-02-24–04-02；DeepStateMap 2022-04-03 起；2014–2022 基线）。
只使用真实数据集；没有数据的战争/日期不显示（不插值、不推测）。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .. import control_zones as CZ
from .. import datafile
from ..registry import LayerModule
from ..timeutil import rec_key

KIND_ZH = {"occupied": "占领/控制区", "contested": "灰色区（状态不明）"}


class WarFrontsLayer(LayerModule):
    id = "war_fronts"
    title = "战争前线"
    order = 7
    default_on = False
    description = "逐日的战争前线：占领/控制区与灰色区（目前：俄乌战争，2014 基线 + 2022-02-24 起逐日）"
    frontend = "modules/war_fronts.js"
    source = "ISW/CTP Assessed Control of Terrain（2022-02-24–04-02）；DeepStateMap 公开历史快照（2022-04-03 起）"

    def load(self, ctx):
        self.dir = Path(ctx.data_dir) / "war_fronts"
        self.wars = []
        # 每场战争一个索引文件 <war>.json.gz（打包版为 .json.xz）
        names = sorted({f.name.rsplit(".json.", 1)[0] for f in self.dir.glob("*.json.[gx]z")}) if self.dir.is_dir() else []
        for n in names:
            d = datafile.read_json(self.dir / f"{n}.json.gz")
            zs = d["zones"]
            for z in zs:
                a, b = CZ.parse(z.get("from")), CZ.parse(z.get("until"), end=True)
                z["_a"] = rec_key(a) if a else -1e9
                z["_b"] = rec_key(b) if b else 1e9
            self.wars.append({"meta": d["war"], "zones": zs})

    def stats(self):
        return {"wars": len(self.wars), "records": sum(len(w["zones"]) for w in self.wars)}

    @lru_cache(maxsize=64)
    def _geom(self, rel: str) -> dict:
        return datafile.read_json(self.dir / rel, {}) or {}

    def layer_query(self, ctx, date, params):
        dk = date.key()
        out = []
        for w in self.wars:
            act = [z for z in w["zones"] if z["_a"] <= dk < z["_b"]]
            if not act:
                continue
            m = w["meta"]
            items = []
            for z in act:
                g = self._geom(z["geometry"]["file"]).get(z.get("layer") or z["kind"])
                if not g:
                    continue
                # 与同类上一条记录比较面积变化（只在同一数据集内比较；跨数据集口径不同）
                prev = None
                if z.get("snapshot"):
                    same = [x for x in w["zones"] if x["kind"] == z["kind"] and x.get("snapshot") and x["_a"] < z["_a"]]
                    if same and same[-1]["dataset"] == z["dataset"]:
                        prev = same[-1]
                items.append({k: z.get(k) for k in ("id", "kind", "name_zh", "controller", "from", "until", "approx", "dataset",
                                                     "snapshot", "snapshot_time", "area_km2", "dates_note", "sources")}
                             | {"kind_zh": KIND_ZH.get(z["kind"], z["kind"]), "geom": g,
                                "delta_km2": round(z["area_km2"] - prev["area_km2"], 1) if prev and z.get("area_km2") is not None else None,
                                "prev_from": prev and prev["from"]})
            ds = {z.get("dataset") for z in act}
            out.append({"war": {k: m.get(k) for k in ("id", "name_zh", "name_en", "data_until", "belligerents")},
                        "datasets": {k: v for k, v in m["datasets"].items() if k in ds},
                        "beyond_data": bool(m.get("data_until")) and dk > rec_key(CZ.parse(m["data_until"])) + 1e-4,
                        "items": items})
        return {"items": out, "total": len(out),
                "note": "只显示有真实逐日数据的战争（目前：俄乌战争）；其他战争没有画不代表没有前线。"}


MODULE = WarFrontsLayer()
