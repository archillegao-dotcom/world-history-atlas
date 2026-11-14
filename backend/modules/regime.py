"""
模块「政权性质」：所选日期该政权的政体（P122，按起止限定）、意识形态（P1142）、
当时国家元首/政府首脑所属政党（P102，按起止限定）、首都（P36，按起止限定）、存在期、国旗，
以及中文维基百科条目首句作为定义（在线获取并缓存；离线时显示 Wikidata 简介）。
另列出该政权当时所属的阵营/同盟（来自阵营数据）。
"""
from __future__ import annotations

from ..zh import disp as _zh_disp

from ..live import wiki
from ..polity import valid_at
from ..registry import ContentModule
from ._common import fmt_time
from ._state_common import split_note, METHOD_ZH, pick_state, resolver
from .leaders import _holding


class RegimeModule(ContentModule):
    id = "regime"
    title = "政权性质"
    order = 7
    description = "政体、执政党、意识形态与维基百科定义"
    frontend = "modules/statepanels.js"
    source = "Wikidata（P122 政体、P1142 意识形态、P102 所属政党、P36 首都）；维基百科条目首句（CC BY-SA）"

    def load(self, ctx):
        self.R = resolver(ctx)

    def stats(self):
        return {"states": len(self.R.states), "mapped_polygons": sum(len(v) for v in self.R.map.values())}

    def query(self, ctx, polity, date, params):
        R = resolver(ctx)
        st, alts = pick_state(ctx, polity, date, params)
        if polity is None:
            return {"items": [], "total": 0, "note": "请在地图上点击一个国家/政权。"}
        if not st:
            from ..territory_info import unverified_note
            return {"items": [], "total": 0, "alternatives": alts,
                    "note": unverified_note(polity, ctx.basemaps.trans) or split_note(params) or "没能把这个地图区域对应到 Wikidata 中当时存在的政权。"}
        dk = date.key()

        def at_date(lst):
            dated = [x for x in lst if x.get("from") or x.get("to")]
            hits = [x for x in dated if valid_at(dk, x.get("from"), x.get("to"))]
            undated = [x for x in lst if not (x.get("from") or x.get("to"))]
            return hits, undated

        group = [st] + [x for x in params.get("_strong", []) if x["id"] != st["id"]]

        def first(field):
            """在主要政权及同名政权中找第一个有该字段（按日期有效）的：返回 (有效值, 无时间值, 来源政权)。"""
            for s_ in group:
                h, u = at_date(s_.get(field, []))
                if h:
                    return h, [], s_
            for s_ in group:
                h, u = at_date(s_.get(field, []))
                if u:
                    return [], u, s_
            return [], [], st

        gov_hit, gov_und, gov_src = first("gov")
        caps_hit, caps_und, _ = first("capitals")
        ideo_hit, ideo_und, ideo_src = first("ideology")
        # 执政党：当时元首/首脑所属政党（P102 带时间的按时间，否则列出并注明未注明时间）
        parties = []
        seenp = set()
        for fld, role in (("hos", "国家元首"), ("hog", "政府首脑")):
            for h in _holding([{"from": x.get("from"), "to": x.get("to"), "p": x["v"]} for s_ in group for x in s_.get(fld, [])], dk):
                if (role, h["p"]) in seenp:
                    continue
                seenp.add((role, h["p"]))
                p = R.persons.get(h["p"], {})
                ph, pu = at_date(p.get("party", []))
                for x in ph + (pu if not ph else []):
                    parties.append({"role": role, "person": R.person_brief(h["p"]), "party": x.get("zh") or x.get("en"),
                                    "party_id": x["v"], "dated": x in ph})
        blocs = []
        act = ctx.shared.get("alliances_active")
        if act:
            ids = {x["id"] for x in group}
            blocs = [{"id": a["id"], "name": a["name"]} for a in act(ctx, date) if ids & set(a["members"])]
        from ..flags import flag_at
        chn = params.get("_chain")
        fl_states = list(group)
        # 同一国家链中同时「至今」的并立政权（如 1949 年以后的中华民国（宪政）与中华人民共和国）：只显示所点政权本身那一行
        now_sel = []
        if chn:
            gids = {x["id"] for x in group}
            now_sel = [r for r in chn["now"] if r.get("qid") in gids] if len(chn["now"]) > 1 else chn["now"]
            now_sel = now_sel or chn["now"]
            for r in now_sel:
                if r.get("qid") in R.states and all(x["id"] != r["qid"] for x in fl_states):
                    fl_states.insert(1, R.states[r["qid"]])
        # 政权链上的当前行比 Wikidata 国家总条目更具体时，面板按当前政权显示。
        # 「法国」Q142 的起点是 481 年（只精确到年），那是把国家追溯到法兰克王国，不是第五共和国的成立日。
        # https://en.wikipedia.org/wiki/French_Fifth_Republic
        # https://www.wikidata.org/wiki/Q142
        display_name = None
        display_from = None
        display_to = None
        extra_note = None
        if chn and len(now_sel) == 1 and now_sel[0].get("zh") and now_sel[0].get("qid") not in (None, st["id"]):
            row = now_sel[0]
            long_y = (st.get("from") or {}).get("y")
            reg_from = row.get("from") or ""
            reg_y = int(reg_from[:4]) if len(reg_from) >= 4 and reg_from[:4].isdigit() else None
            # 只在国家总条目比当前政权早得多时改显示（法国 Q142 的 481 年对第五共和国）。
            # 不改那些起点本来就在近代的国家，避免把面板标题整表换掉。
            if long_y is not None and reg_y is not None and long_y < 800 and reg_y >= 1700:
                display_name = row["zh"]
                display_from = row.get("from")
                display_to = row.get("to")
                long_from = fmt_time(st.get("from")) if st.get("from") else "未记录"
                extra_note = (f"所选日期的政权是{row['zh']}"
                              + (f"（{row.get('from')} 起）" if row.get("from") else "")
                              + f"。Wikidata 条目「{st.get('zh') or st.get('en') or st['id']}」的起点记为 {long_from}，"
                              "那是把后来的国家追溯到更早的政治体，不是这个政权的成立日。")
        if params.get("_dynasty_before_start"):
            extra_note = (f"底图多边形名称是 {params['_dynasty_before_start']}（周，不是商）。"
                          "周灭商的通行学术年代约前1046年（夏商周断代工程；另有约前1050至前1027年的估计）。"
                          "传统纪年里的约前1122年不作为依据。这张底图是公元前1500年的快照，要到下一张才更换，"
                          "所以前1046年以前这块仍然单独画出，不能再标成第二块商朝。"
                          " https://en.wikipedia.org/wiki/Western_Zhou"
                          " https://en.wikipedia.org/wiki/Xia%E2%80%93Shang%E2%80%93Zhou_Chronology_Project")
            display_name = "周（底图名称；周灭商约前1046年）"
        fl, fl_dated, fl_from, fl_src = flag_at(ctx.data_dir, fl_states, dk)
        summ = wiki.summary(st.get("zhwiki"), st.get("enwiki")) if params.get("online", True) else None
        term = lambda x: {"id": x["v"], "name": _zh_disp(x.get("zh") or x.get("en") or x["v"]), "en": x.get("en")}
        out = {"items": [], "total": 1, "kind": "regime",
                "state": {"id": st["id"], "name": display_name or _zh_disp(st.get("zh") or st.get("en")), "en": st.get("en"),
                          "desc": st.get("desc"),
                          "from": display_from if display_from is not None else (fmt_time(st.get("from")) if st.get("from") else None),
                          "to": display_to if display_from is not None else (fmt_time(st.get("to")) if st.get("to") else None),
                          "flag": wiki.commons_thumb(fl, 160), "flag_file": fl, "flag_dated": fl_dated,
                          "flag_note": (fl_src if fl else (fl_src or "Wikidata 没有该政权的国旗记录")) if (fl_src or not fl) else None,
                          "zhwiki": st.get("zhwiki"), "enwiki": st.get("enwiki")},
                "alternatives": [{**a, "method_zh": METHOD_ZH.get(a["method"], a["method"])} for a in alts],
                "gov": [term(x) for x in gov_hit], "gov_undated": [term(x) for x in gov_und] if not gov_hit else [],
                "ideology": [term(x) for x in ideo_hit + ideo_und],
                "gov_from": None if gov_src is st else f'{gov_src.get("zh") or gov_src.get("en")}，{gov_src["id"]}',
                "ideology_from": None if ideo_src is st else f'{ideo_src.get("zh") or ideo_src.get("en")}，{ideo_src["id"]}',
                "capital": [_zh_disp(x.get("name")) for x in (caps_hit or caps_und) if x.get("name")][:3],   # 没有中文/英文名称的条目不显示（否则出现「、吉隆坡」）
                "parties": parties, "blocs": blocs,
                "chain": chn and {"country": chn["country_zh"], "now": [r["zh"] for r in now_sel],
                                  "rows": [{k: r.get(k) for k in ("from", "to", "zh", "qid", "parallel", "note", "src", "current")} for r in chn["rows"]]},
                "definition": wiki.first_sentence(summ["extract"]) if summ else None,
                "definition_src": summ and {"lang": summ["lang"], "url": summ["url"], "title": summ["title"]},
                "note": " ".join(x for x in ("政体等字段以 Wikidata 为准；没有时间限定的值单独标出（可能不适用于所选日期）。", extra_note) if x)}
        if polity and isinstance(polity["props"].get("fid"), int) and polity["props"].get("TERRITORY"):
            trec = ctx.basemaps.trans.terr[polity["props"]["fid"] - 200000]
            out["geom_note"] = trec.get("geom_note")
        from ..ganden import finish_regime
        return finish_regime(out, polity, date, params)


MODULE = RegimeModule()
