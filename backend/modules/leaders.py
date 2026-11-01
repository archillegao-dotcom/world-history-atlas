"""
模块「领导人」：所选日期该政权的国家元首（P35）、政府首脑（P6），以及管辖区（P1001）为该政权的
重要职位（P39 任职者，含起止时间限定），如「中华民国总统」「行政院院长」「立法院院长」。

任职判断：开始 ≤ 日期 ≤ 结束；没有结束时间的，若在开始之后、所选日期之前该职位没有新的任职者，
且距开始不超过 15 年，则视为仍在任（否则不显示，避免猜测）。没有开始时间的不显示。
每个职位可点开「机构卡片」（职位与所领导机构 P2389 的维基百科摘要）；每个人可点开人物页面。
"""
from __future__ import annotations

import re

from ..polity import valid_at
from ..registry import ContentModule
from ..timeutil import HDate, rec_key
from ._common import fmt_time
from ._state_common import split_note, METHOD_ZH, pick_state, resolver


def _start_key(t):
    """任期开始：只精确到年/月时取该年/月的第一天（HDate(y,0,0) 的数值是年中，不能直接用）。"""
    if not t:
        return None
    if not t.get("m"):
        return HDate(t["y"], 1, 1).key()
    if not t.get("d"):
        return HDate(t["y"], t["m"], 1).key()
    return rec_key(t)


def _end_key(t):
    """任期结束：只精确到年/月时取该年/月的最后一天。"""
    if not t:
        return None
    if not t.get("m"):
        return HDate(t["y"], 12, 31).key()
    if not t.get("d"):
        return HDate(t["y"], t["m"], 28).key() + 0.0001
    return rec_key(t)


def _single_holder(holders):
    """该职位通常同一时间只有一人（精确到日的任期两两重叠的比例 < 10%）。"""
    iv = sorted((rec_key(h["from"]), rec_key(h["to"])) for h in holders
                if h.get("from", {}) and h["from"].get("d") and h.get("to") and h["to"].get("d"))
    if len(iv) < 4:
        return False
    ov = sum(1 for (a1, b1), (a2, b2) in zip(iv, iv[1:]) if a2 < b1 - 0.02)   # 允许约一周的交接
    return ov / (len(iv) - 1) < 0.1


def _holding(holders, dk, statement_mode=False):
    """返回在 dk 时在任的任职记录列表。
    卸任时间只精确到年/月（按该年/月末计）时，若同一职位（通常只有一人在任）的下一任在这段时间内、
    以精确到日的日期就任，则以下一任的就任日作为卸任日（例：阎锡山 1949–1950 → 陈诚 1950-03-07 就任）。"""
    out = []
    starts = sorted(_start_key(h.get("from")) for h in holders if h.get("from"))
    exact_starts = sorted(rec_key(h["from"]) for h in holders if h.get("from") and h["from"].get("d"))
    single = None
    for h in holders:
        a, b = _start_key(h.get("from")), _end_key(h.get("to"))
        if a is None or a > dk:
            continue
        if b is not None:
            if dk <= b:
                to = h.get("to") or {}
                if not to.get("d") and any(a < s <= dk for s in exact_starts):
                    if single is None:
                        single = _single_holder(holders)
                    if single:
                        continue
                out.append(h)
            continue
        later = [s for s in starts if a < s <= dk]
        if not later and dk - a <= 15:
            out.append(h)
    return out


# 各国传统纪年中可靠性存疑的早期君主：在位年代按国际学界共识标注为「传说/传统纪年」（显示原值，加注释）
LEGENDARY = {
    # 中国先秦君主（Q38702033 "Chinese king"）：公元前 841 年（共和元年）是中国史上第一个有确切纪年的年份；
    # 此前夏、商、西周诸王的在位年代来自《史记》《竹书纪年》等传统纪年及后世推算，国际学界没有公认的确切年代
    "Q38702033": (-841, "传统纪年：公元前 841 年（共和元年）以前的中国君主在位年代来自《史记》等传统史书与后世推算，国际学界没有公认的确切年代（夏代君主是否为历史人物仍有争议）；所示年份仅供参考。"),
    # 日本天皇：第 29 代钦明天皇（539 年即位）以前的在位年份来自《日本书纪》等传统纪年，学界认为不可靠
    # Q208233 = Emperor of Japan（已核对：Wikidata 描述 "head of state of Japan"）
    "Q208233": (539, "日本早期天皇（6 世纪以前）的在位年代来自《古事记》《日本书纪》的传统纪年，国际学界认为是传说或不可靠。"),
}
# 按政权：早期年代来自传统史书（如《三国史记》《三国遗事》）、国际学界认为不可靠的时段（年份以前）
# 依据：en.wikipedia「Gojoseon」「Goguryeo」「Baekje」「Silla」「Emperor Jimmu」等条目的史学讨论
LEGENDARY_STATE = {
    "Q28405": (-108, "古朝鲜的建国年代（檀君，公元前 2333 年）来自 13 世纪《三国遗事》的传说纪年；国际学界只把公元前 4–2 世纪的古朝鲜视为可考的历史政权。"),
    "Q28370": (53, "高句丽的建国年代（公元前 37 年）与早期诸王来自 12 世纪《三国史记》的传统纪年；国际学界通常认为第 6 代太祖王（公元 53 年起）以后的记载才较可靠。"),
    "Q28428": (346, "百济的建国年代（公元前 18 年）与早期诸王来自《三国史记》的传统纪年；国际学界通常认为近肖古王（346 年即位）以后的记载才较可靠。"),
    "Q28456": (356, "新罗的建国年代（公元前 57 年）与早期诸王来自《三国史记》的传统纪年；国际学界通常认为奈勿尼师今（356 年即位）以后的记载才较可靠。"),
    "Q17": (539, "日本 6 世纪以前的天皇在位年代来自《古事记》《日本书纪》的传统纪年，国际学界认为是传说或不可靠。"),
}


# Wikidata 中文标签不贴切的职位：显示用名称（只改显示，不改数据）
OFFICE_NAME_ZH = {"Q38702033": "王（君主）"}   # Wikidata zh 标签为「中国国王」，夏商周时期的称号为「王」


# 外交使节/使馆不是本国领导职位（Wikidata 常把「X 国驻华大使」的管辖区记为驻在国，导致出现在驻在国面板里）
_ENVOY_EN = re.compile(r"(?i)\b(ambassadors?|embassy|envoys?|high commissioners? to|chargés? d'affaires|consuls?-general)\b")
_ENVOY_ZH = re.compile(r"驻.*(大使|使馆|公使|领事|专员)")


# 配偶头衔（第一夫人、首相配偶、王后/王室配偶等）与职业荣誉头衔（御用大律师 QC/KC/SC）不是领导职位，不在面板中显示
_SPOUSE_EN = re.compile(r"(?i)\b(first|second) (lad(y|ies)|gentlem[ae]n|spouses?)\b|\bspouses? of\b|\bconsorts?\b|\b(wife|husband) of\b"
                        r"|\b(queen'?s|king'?s|senior) counsel\b")
_SPOUSE_ZH = re.compile(r"第一夫人|第一先生|夫人$|配偶|王后列表|^皇后$|^王后$|^可敦$|皇后列表|王室法律顾问|御用大律师|资深大律师")


def is_envoy(o):
    """不属于领导职位的条目：外交使节/使馆、配偶头衔、律师荣誉头衔。"""
    en, zh = o.get("en") or "", o.get("zh") or ""
    return bool(_ENVOY_EN.search(en) or _ENVOY_ZH.search(zh) or _SPOUSE_EN.search(en) or _SPOUSE_ZH.search(zh))


def legend_note(o, h):
    pos = o.get("pos") or o["id"]
    if pos in LEGENDARY and h.get("from") and h["from"]["y"] < LEGENDARY[pos][0]:
        return LEGENDARY[pos][1]
    return None


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
                    "note": split_note(params) or "没能把这个地图区域对应到 Wikidata 中当时存在的政权（名称不匹配、首都也不在此范围内）。"}
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
                                  "to": fmt_time(h.get("to")) if h.get("to") else None,
                                  "src": None if s_ is st else (s_.get("zh") or s_.get("en"))})
        offices = []
        ofs, osrc = {}, {}
        for s_ in group:
            for o in R.office_by_state.get(s_["id"], []):
                if o["id"] not in ofs:
                    ofs[o["id"]] = o
                    osrc[o["id"]] = None if s_ is st else (s_.get("zh") or s_.get("en"))
        for o in sorted(ofs.values(), key=lambda o: -o["sl"]):
            if is_envoy(o):
                continue
            hs = _holding(o.get("holders", []), dk)
            if not hs:
                continue
            offices.append({"office": {"id": o["id"], "name": OFFICE_NAME_ZH.get(o.get("pos")) or o.get("zh") or o.get("en"), "en": o.get("en"),
                                       "desc": o.get("desc")},
                            "virtual": bool(o.get("virtual")), "juris": o.get("juris_zh"), "src": osrc.get(o["id"]),
                            "holders": [{"person": R.person_brief(h["p"]), "from": fmt_time(h.get("from")),
                                         "to": fmt_time(h.get("to")) if h.get("to") else None,
                                         "to_note": h.get("to_inferred"), "legend": legend_note(o, h)} for h in hs[:4]]})
            if len(offices) >= 30:
                break
        # 有任职者但都没有记录任期的职位：只列出名称（可点开机构卡片查看历任者），不猜测谁在任
        undated = []
        for o in sorted(ofs.values(), key=lambda o: -o["sl"]):
            hs = o.get("holders", [])
            if is_envoy(o):
                continue
            if hs and not any(h.get("from") for h in hs) and len(undated) < 12:
                undated.append({"id": o["id"], "name": o.get("zh") or o.get("en"), "n": len(hs)})
            elif hs and o["id"] not in {x["office"]["id"] for x in offices}:
                nd = sum(1 for h in hs if not h.get("from"))
                if nd * 2 >= len(hs) and len(undated) < 12:
                    undated.append({"id": o["id"], "name": o.get("zh") or o.get("en"), "n": nd})
        # 年号（Wikidata 年号条目的起止时间；同一时间可能有多个政权的年号）
        eras = []
        for s_ in group:
            for e in R.eras_by_state.get(s_["id"], []):
                if valid_at(dk, e.get("from"), e.get("to") or e.get("from")) or (
                        e.get("to") is None and rec_key(e["from"]) <= dk < rec_key(e["from"]) + 1):
                    eras.append({"id": e["id"], "name": e.get("zh") or e.get("en"), "en": e.get("en"),
                                 "from": fmt_time(e.get("from")), "to": fmt_time(e.get("to")) if e.get("to") else None})
        terr = None
        if polity["props"].get("TERRITORY"):
            from ..territory_info import info
            t = info(polity["props"].get("NAME"), polity["props"].get("TERR_CAT"))
            trec = ctx.basemaps.trans.terr[polity["props"]["fid"] - 200000]
            chain = [R.states[q] for q in (trec.get("chain") or []) if q in R.states]
            from ..territory_info import SOV_ZH
            sov = polity["props"].get("SUBJECTO")
            terr = {**t, "sovereign": SOV_ZH.get(sov, sov), "geom_note": trec.get("geom_note"),
                    "history": [{"id": c["id"], "name": c.get("zh") or c.get("en"), "from": fmt_time(c.get("from")),
                                 "to": fmt_time(c.get("to")) if c.get("to") else None} for c in chain]}
        n = len(heads) + len(offices)
        return {"items": [], "total": n, "kind": "leaders",
                "state": {"id": st["id"], "name": st.get("zh") or st.get("en"), "en": st.get("en"), "desc": st.get("desc")},
                "alternatives": [{**a, "method_zh": METHOD_ZH.get(a["method"], a["method"])} for a in alts],
                "merged": [{"id": x["id"], "name": x.get("zh") or x.get("en")} for x in group[1:]],
                "heads": heads, "offices": offices, "undated_offices": undated, "eras": eras[:6],
                "state_note": " ".join(x for x in (st.get("curated_note"), st.get("xcheck_note"),
                                                   (LEGENDARY_STATE[st["id"]][1] if st["id"] in LEGENDARY_STATE
                                                    and date.y < LEGENDARY_STATE[st["id"]][0] else None)) if x) or None, "territory": terr,
                "note": "数据来自 Wikidata 的职务记录；没有起止时间的任职记录不显示。" +
                        ("" if n else "这一日期没有找到带时间的任职记录。")}


MODULE = LeadersModule()
