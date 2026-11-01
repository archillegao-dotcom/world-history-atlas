"""
模块「领导人」：所选日期该政权的国家元首（P35）、政府首脑（P6），以及管辖区（P1001）为该政权的
重要职位（P39 任职者，含起止时间限定），如「中华民国总统」「行政院院长」「立法院院长」。

任职判断：开始 ≤ 日期 ≤ 结束；没有结束时间的，若在开始之后、所选日期之前该职位没有新的任职者，
且距开始不超过 15 年，则视为仍在任（否则不显示，避免猜测）。没有开始时间的不显示。
每个职位可点开「机构卡片」（职位与所领导机构 P2389 的维基百科摘要）；每个人可点开人物页面。
"""
from __future__ import annotations

from ..polity import valid_at
from ..registry import ContentModule
from ..timeutil import rec_key
from ._common import fmt_time
from ._state_common import METHOD_ZH, pick_state, resolver


def _holding(holders, dk, statement_mode=False):
    """返回在 dk 时在任的任职记录列表。"""
    out = []
    starts = sorted(rec_key(h.get("from")) for h in holders if h.get("from"))
    for h in holders:
        a, b = rec_key(h.get("from")), rec_key(h.get("to"))
        if b is not None:  # 只精确到年/月的卸任时间视为该年/月末
            t = h["to"]
            b += 0.999 if not t.get("m") else (0.08 if not t.get("d") else 0)
        if a is None or a > dk:
            continue
        if b is not None:
            if dk <= b:
                out.append(h)
            continue
        later = [s for s in starts if a < s <= dk]
        if not later and dk - a <= 15:
            out.append(h)
    return out


class LeadersModule(ContentModule):
    id = "leaders"
    title = "领导人"
    order = 8
    description = "所选日期的国家元首、政府首脑与重要职位任职者（Wikidata P35 / P6 / P39）"
    frontend = "modules/statepanels.js"
    source = "Wikidata（P35 国家元首、P6 政府首脑、P39 担任职务及起止时间、P1001 管辖区，CC0）"

    def load(self, ctx):
        self.R = resolver(ctx)

    def stats(self):
        return {"offices": len(self.R.offices), "persons": len(self.R.persons)}

    def query(self, ctx, polity, date, params):
        R = resolver(ctx)
        st, alts = pick_state(ctx, polity, date, params)
        if polity is None:
            return {"items": [], "total": 0, "note": "请在地图上点击一个国家/政权。"}
        if not st:
            return {"items": [], "total": 0, "alternatives": alts,
                    "note": "没能把这个地图区域对应到 Wikidata 中当时存在的政权（名称不匹配、首都也不在此范围内）。"}
        dk = date.key()
        # 同一地区当时存在的同名政权（如「中华民国」有 1912–1949 与 1912 至今两个条目）合并显示
        group = [st] + [x for x in params.get("_strong", []) if x["id"] != st["id"]]
        heads, seen = [], set()
        for s_ in group:
            for fld, role in (("hos", "国家元首"), ("hog", "政府首脑")):
                for h in _holding([{"from": x.get("from"), "to": x.get("to"), "p": x["v"]} for x in s_.get(fld, [])], dk):
                    if (role, h["p"]) in seen:
                        continue
                    seen.add((role, h["p"]))
                    heads.append({"role": role, "person": R.person_brief(h["p"]), "from": fmt_time(h.get("from")),
                                  "to": fmt_time(h.get("to")) if h.get("to") else None})
        offices = []
        ofs = {o["id"]: o for s_ in group for o in R.office_by_state.get(s_["id"], [])}
        for o in sorted(ofs.values(), key=lambda o: -o["sl"]):
            hs = _holding(o.get("holders", []), dk)
            if not hs:
                continue
            offices.append({"office": {"id": o["id"], "name": o.get("zh") or o.get("en"), "en": o.get("en"),
                                       "desc": o.get("desc")},
                            "holders": [{"person": R.person_brief(h["p"]), "from": fmt_time(h.get("from")),
                                         "to": fmt_time(h.get("to")) if h.get("to") else None} for h in hs[:4]]})
            if len(offices) >= 30:
                break
        # 有任职者但都没有记录任期的职位：只列出名称（可点开机构卡片查看历任者），不猜测谁在任
        undated = []
        for o in sorted(ofs.values(), key=lambda o: -o["sl"]):
            hs = o.get("holders", [])
            if hs and not any(h.get("from") for h in hs) and len(undated) < 12:
                undated.append({"id": o["id"], "name": o.get("zh") or o.get("en"), "n": len(hs)})
            elif hs and o["id"] not in {x["office"]["id"] for x in offices}:
                nd = sum(1 for h in hs if not h.get("from"))
                if nd * 2 >= len(hs) and len(undated) < 12:
                    undated.append({"id": o["id"], "name": o.get("zh") or o.get("en"), "n": nd})
        n = len(heads) + len(offices)
        return {"items": [], "total": n, "kind": "leaders",
                "state": {"id": st["id"], "name": st.get("zh") or st.get("en"), "en": st.get("en"), "desc": st.get("desc")},
                "alternatives": [{**a, "method_zh": METHOD_ZH.get(a["method"], a["method"])} for a in alts],
                "heads": heads, "offices": offices, "undated_offices": undated,
                "note": "数据来自 Wikidata 的职务记录；没有起止时间的任职记录不显示。" +
                        ("" if n else "这一日期没有找到带时间的任职记录。")}


MODULE = LeadersModule()
