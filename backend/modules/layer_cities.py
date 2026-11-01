"""
地图图层「主要城市」：只显示在所选日期已经存在（且未废弃）的城市。

存在时间判断（数据均来自 Wikidata）：
  1. 有 P571 建立时间 → 从该时间起；有 P576 废弃时间 → 到该时间止；
  2. 没有建立时间 → 用「已知最早存在证据」：作为某国首都的起始时间、带日期的历史官方名称的起始时间；
  3. 以上都没有 → 只在 1800 年以后显示（保守做法，避免把现代城市画进古代地图）。
名称：若 P1448 官方名称中有当时有效的中文名（如 1928–1937 年的「北平市」），用它；否则用当前中文标签；
      当时有效的其他语言官方名称（如 Константинопол / Βυζάντιον）放在提示信息里。
首都：P1376「首都所属」在当日有效（有起止限定按限定；无限定则按所属国家自身的存在期）且所属是国家级政权。
排名：sitelinks + 人口（对数）；前端按缩放级别与屏幕上的标签碰撞决定显示多少。
"""
from __future__ import annotations

from pathlib import Path

from ..registry import LayerModule
from ..timeutil import rec_key
from ._common import load_records

NO_INCEPTION_FROM = 1800.0


class CitiesLayer(LayerModule):
    id = "cities"
    title = "主要城市"
    order = 5
    description = "所选日期已存在的主要城市（★ 为当时的国家首都）"
    frontend = "modules/cities.js"
    source = "Wikidata（P571 建立、P576 废弃、P1448 官方名称、P1376 首都所属、P1082 人口，CC0）"

    def load(self, ctx):
        self.recs = []
        for r in load_records(Path(ctx.data_dir) / "cities.json.gz"):
            start = rec_key(r.get("from"))
            evidence = [rec_key(c.get("from")) or rec_key(c.get("state_from")) for c in r.get("capital", [])]
            evidence += [rec_key(n.get("from")) for n in r.get("names", [])]
            evidence = [e for e in evidence if e is not None]
            if start is None:
                start = min(evidence) if evidence else NO_INCEPTION_FROM
                r["_inferred"] = bool(evidence)
            r["_from"] = start
            r["_to"] = rec_key(r.get("to"))
            self.recs.append(r)
        self.recs.sort(key=lambda r: -r.get("score", 0))

    def stats(self):
        return {"records": len(self.recs)}

    @staticmethod
    def _valid(dk, a, b):
        ka, kb = rec_key(a), rec_key(b)
        return (ka is None or ka <= dk) and (kb is None or dk <= kb)

    def layer_query(self, ctx, date, params):
        dk = date.key()
        limit = int(params.get("limit") or 4000)
        out = []
        for r in self.recs:
            if r["_from"] > dk or (r["_to"] is not None and dk > r["_to"]):
                continue
            name = r.get("zh") or r.get("en")
            hist = []
            for n in r.get("names", []):
                if self._valid(dk, n.get("from"), n.get("to")):
                    if (n.get("lang") or "").startswith("zh"):
                        name = n["name"]
                    else:
                        hist.append(n["name"])
            cap = False
            for c in r.get("capital", []):
                if c.get("from") or c.get("to"):
                    ok = self._valid(dk, c.get("from"), c.get("to"))
                else:  # 无限定：用所属国家的存在期；国家存在期未知则不判定为首都
                    ok = (c.get("state_from") or c.get("state_to")) and self._valid(dk, c.get("state_from"), c.get("state_to"))
                if ok:
                    cap = True
                    break
            # 显示用：去掉中文行政区划后缀「市」（如「北京市」→「北京」），只影响地图标签
            if name and len(name) > 2 and name.endswith("市"):
                name = name[:-1]
            out.append({"id": r["id"], "name": name, "en": r.get("en"), "coord": r["coord"], "capital": cap,
                        "score": r.get("score", 0), "pop": r.get("pop"), "hist": hist[:3],
                        "inferred": r.get("_inferred", False) or r.get("from") is None,
                        "wiki": r.get("zhwiki") or r.get("enwiki")})
            if len(out) >= limit:
                break
        return {"items": out, "total": len(out),
                "note": "没有建立时间记录的城市：用作为首都/历史名称的最早日期推断；仍无记录则只在1800年后显示"}


MODULE = CitiesLayer()
