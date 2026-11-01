"""
地图图层「阵营地图」：按所选日期有效的同盟/阵营成员资格给政权着色。

数据：data/alliances.json.gz（tools/build_states.py）——Wikidata 中 military alliance、
multinational military coalition、alliance、koinon 及其子类，且至少有 2 个政权成员。
成员资格：成员记录自己的加入/退出时间（P580/P582 限定）优先；没有时用阵营本身的存在期（P571/P576 或 P580/P582）。
地图多边形 → 政权：用 backend/polity.py 的「强」候选（名称匹配等；当时存在的强候选里只要有一个是成员就着色）。
只靠首都/坐标落在范围内的弱候选（多为下级行政区）不参与着色。
"""
from __future__ import annotations

from pathlib import Path

from ..polity import alive, valid_at
from ..registry import LayerModule
from ..timeutil import rec_key
from ._common import load_records
from ._state_common import resolver


class AlliancesLayer(LayerModule):
    id = "alliances"
    title = "阵营地图"
    order = 6
    default_on = False
    description = "按同盟/阵营给国家着色（可选择显示哪些阵营），点击图例查看阵营详情"
    frontend = "modules/alliances.js"
    source = "Wikidata（military alliance 等；成员 P527/P710/P1891/P463 及加入/退出时间，CC0）"

    def load(self, ctx):
        self.recs = load_records(Path(ctx.data_dir) / "alliances.json.gz")
        self.by_id = {a["id"]: a for a in self.recs}
        ctx.shared["alliances"] = self.recs
        ctx.shared["alliances_active"] = self.active   # 供「政权性质」模块列出所属阵营

    def stats(self):
        return {"records": len(self.recs)}

    def active(self, ctx, date):
        R = resolver(ctx)
        dk = date.key()
        out = []
        for a in self.recs:
            if not valid_at(dk, a.get("from"), a.get("to")):
                continue
            # 既没有解散时间、成员也都没有加入/退出时间的阵营：无法知道何时结束，只在成立后 100 年内显示
            # （例如 Hellenic League 公元前 481 年成立，Wikidata 没有解散时间，否则会一直显示到今天）
            if not a.get("to") and a.get("from") and not any(m.get("from") or m.get("to") for m in a["members"]) \
                    and dk > rec_key(a["from"]) + 100:
                continue
            # 成员资格在该日期有效，且成员政权本身当时存在（例如 1942 年已不存在的普鲁士王国不算）
            mem = []
            for m in self.recs_members(a):
                st = R.states.get(m["s"])
                if not valid_at(dk, m.get("from") or a.get("from"), m.get("to") or a.get("to")):
                    continue
                if st and not alive(dk, st):
                    continue
                # 成员记录没有自己的加入时间时，要求该政权在阵营成立时（前后 5 年内）已经存在，
                # 以排除「古代同盟的成员写成了现代国家」这类建模不一致（如 Hellenic League → 现代希腊）
                if st and not m.get("from") and a.get("from") and st.get("from") and rec_key(st["from"]) > rec_key(a["from"]) + 5:
                    continue
                if m["s"] not in mem:
                    mem.append(m["s"])
            if len(mem) >= 2 and (a.get("from") or any(m.get("from") for m in a["members"])):
                out.append({"id": a["id"], "name": a.get("zh") or a.get("en"), "en": a.get("en"), "sl": a["sl"],
                            "members": mem, "no_end": not a.get("to")})
        return out

    @staticmethod
    def recs_members(a):
        return a.get("members", [])

    def layer_query(self, ctx, date, params):
        R = resolver(ctx)
        snap = ctx.basemaps.snapshot_at(date)
        # 多边形 → 当时存在的候选政权 QID
        fids = {}
        for fid in ctx.basemaps.features(snap):
            c = [x["state"]["id"] for x in R.strong(snap, fid, date)]
            if c:
                fids[str(fid)] = c
        act = self.active(ctx, date)
        return {"snapshot": snap, "alliances": act, "polity_states": fids, "total": len(act),
                "note": "只列出有明确时间信息（阵营或成员的起止时间）的阵营"}


MODULE = AlliancesLayer()
