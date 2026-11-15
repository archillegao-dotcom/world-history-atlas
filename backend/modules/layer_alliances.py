"""
地图图层「阵营地图」：按所选日期有效的同盟/阵营成员资格给政权着色。

数据：data/alliances.json.gz（tools/build_states.py）——Wikidata 中 military alliance、
multinational military coalition、alliance、koinon 及其子类，且至少有 2 个政权成员。
成员资格：成员记录自己的加入/退出时间（P580/P582 限定）优先；没有时用阵营本身的存在期（P571/P576 或 P580/P582）。
地图多边形 → 政权：用 backend/polity.py 的「强」候选（名称匹配等；当时存在的强候选里只要有一个是成员就着色）。
只靠首都/坐标落在范围内的弱候选（多为下级行政区）不参与着色。
"""
from __future__ import annotations

from ..zh import disp as _zh_disp

from pathlib import Path

from ..polity import alive, valid_at
from ..registry import LayerModule
from ..timeutil import rec_key
from ._common import load_records
from ._state_common import resolver


DATE_FIXES = {
    # 轴心国：1936-10-23 德意签署议定书（柏林—罗马轴心）；1945-09-02 日本签署投降书
    "Q43056": {"from": {"y": 1936, "m": 10, "d": 23, "p": 11}, "to": {"y": 1945, "m": 9, "d": 3, "p": 11},
               "sources": ["https://zh.wikipedia.org/wiki/%E8%BD%B4%E5%BF%83%E5%9B%BD",
                           "https://en.wikipedia.org/wiki/Axis_powers", "https://en.wikipedia.org/wiki/Tripartite_Pact"],
               # 成员加入/退出（《三国同盟条约》签署/退出日期，to 不含）。Q600018 是 1920–1946 的匈牙利王国，与 Q171150 同一签约日。
               "members": {"Q171150": ("1940-11-20", None), "Q600018": ("1940-11-20", None),
                           "Q203493": ("1940-11-23", "1944-08-23"),
                           "Q147909": ("1941-03-01", "1944-09-08"), "Q172579": (None, "1943-09-08"),
                           "Q191077": ("1941-03-25", "1941-03-27")}},
    # 同盟国。Wikidata 未记加入日时会沿用阵营的 1939 年，于是 1940 年的苏联、南斯拉夫被涂成同盟。
    # 苏联 1941-06-22 德国入侵后才与轴心交战（英苏协定是 1941-07-12）：
    #   https://en.wikipedia.org/wiki/Operation_Barbarossa
    #   https://en.wikipedia.org/wiki/Anglo-Soviet_Agreement
    # 南斯拉夫王国 1941-04-06 轴心入侵后继续作战，1940 年不是同盟国：
    #   https://en.wikipedia.org/wiki/Invasion_of_Yugoslavia
    # 法国按当时政权，不用「法国」Q142 覆盖 1939–1944：
    #   第三共和国 1939-09-03 至 1940-06-22 贡比涅停战 https://en.wikipedia.org/wiki/Armistice_of_22_June_1940
    #   维希不是同盟国。临时政府自 1944-08-25 巴黎解放。自由法国没有单独多边形，本批不新造边界。
    "Q329888": {"members": {"Q15180": ("1941-06-22", None), "Q191077": ("1941-04-06", None),
                            "Q70802": ("1939-09-03", "1940-06-22"),
                            "Q783684": ("1944-08-25", "1946-10-27"),
                            "Q69829": ("1946-10-27", "1958-10-04"),
                            "Q142": ("1944-08-25", None)}},
}

# P463 写成轴心成员、但不是签署国的附庸/保护国/殖民概念。不计入成员国（CLIENT 另行虚线）。
NOT_FULL_MEMBER = {
    "Q30623", "Q696242", "Q154401", "Q153128", "Q153660", "Q5589262", "Q152750", "Q926295",
}


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
        # 阵营起止时间的人工修正（Wikidata 只有年份精度，且起点晚于史实）
        for qid, fx in DATE_FIXES.items():
            a = self.by_id.get(qid)
            if a:
                a["_wd_from"] = a.get("from")
                a.update({k: v for k, v in fx.items() if k in ("from", "to")})
                a["date_fix"] = {k: v for k, v in fx.items() if k != "members"}
                def _d(x):
                    if not x: return None
                    y, m, d = map(int, x.split("-")); return {"y": y, "m": m, "d": d, "p": 11}
                present = {m["s"] for m in a.get("members", [])}
                for mq, (f0, t0) in fx.get("members", {}).items():
                    if mq not in present:
                        a.setdefault("members", []).append({"s": mq, "from": _d(f0), "to": _d(t0), "via": "curated"})
                        present.add(mq)
                for m in a.get("members", []):
                    if m["s"] in fx.get("members", {}):
                        f0, t0 = fx["members"][m["s"]]
                        m["from"], m["to"] = _d(f0) or m.get("from"), _d(t0) or m.get("to")
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
                if m["s"] in NOT_FULL_MEMBER:
                    continue
                st = R.states.get(m["s"])
                if not valid_at(dk, m.get("from") or a.get("from"), m.get("to") or a.get("to")):
                    continue
                if st and not alive(dk, st):
                    continue
                # 成员记录没有自己的加入时间时，要求该政权在阵营成立时（前后 5 年内）已经存在，
                # 以排除「古代同盟的成员写成了现代国家」这类建模不一致（如 Hellenic League → 现代希腊）
                af = a.get("_wd_from") or a.get("from")
                if st and not m.get("from") and af and st.get("from") and rec_key(st["from"]) > rec_key(af) + 5:
                    continue
                if m["s"] not in mem:
                    mem.append(m["s"])
            if len(mem) >= 2 and (a.get("from") or any(m.get("from") for m in a["members"])):
                out.append({"id": a["id"], "name": _zh_disp(a.get("zh") or a.get("en")), "en": a.get("en"), "sl": a["sl"],
                            "members": mem, "no_end": not a.get("to")})
        return out

    @staticmethod
    def recs_members(a):
        return a.get("members", [])

    def layer_query(self, ctx, date, params):
        R = resolver(ctx)
        snap = ctx.basemaps.snapshot_at(date)
        # 多边形 → 当时存在的候选政权 QID
        fids, via, client = {}, {}, {}
        for fid, f in ctx.basemaps.features(snap).items():
            c = [x["state"]["id"] for x in R.strong(snap, fid, date)]
            ds = f"{date.y:04d}-{(date.m or 1):02d}-{(date.d or 1):02d}" if date.y > 0 else ""
            puppet = any((cl := CLIENT.get(q)) and cl["from"] <= ds < cl["to"] for q in c)
            occ = [] if puppet else occupiers(f.get("props") or {})
            if occ:   # 占领区继承占领国的阵营。附庸不再叠成占领国的实色成员国。
                via[str(fid)] = occ
                c = c + [q for q in occ if q not in c]
            if c:
                fids[str(fid)] = c
                ds = f"{date.y:04d}-{(date.m or 1):02d}-{(date.d or 1):02d}" if date.y > 0 else ""
                for q in c:
                    cl = CLIENT.get(q)
                    if cl and cl["from"] <= ds < cl["to"]:
                        client[str(fid)] = {"bloc": cl["bloc"], "tag": cl["tag"], "state": q}
        act = self.active(ctx, date)
        return {"snapshot": snap, "alliances": act, "polity_states": fids, "occupier_of": via, "client_of": client, "total": len(act),
                "note": "只列出有明确时间信息（阵营或成员的起止时间）的阵营"}


# 二战占领方 → 占领国 QID（Stanford「Building the New Order」WW2_STATUS 字段，如 "German, Italian-occupied"）
OCCUPIER_QID = {"German": "Q7318", "Italian": "Q172579", "Japanese": "Q188712",
                "Hungarian": "Q171150", "Romanian": "Q203493", "Bulgarian": "Q147909"}


# 控制区（tools/curated_src）里由轴心国扶植/占领的政权 → 扶植国/占领国
PATRON = {q: "Q188712" for q in (
    "Q697837", "Q10905486", "Q701967", "Q362078", "Q713768", "Q715645", "Q15243087", "Q702310", "Q4065239",
    "Q3175954", "Q2072172", "Q6158903", "Q65270011", "Q704358", "Q1521499", "Q704714", "Q708865", "Q701337",
    "Q16673775", "Q338248", "Q696242", "Q30623")}
PATRON["Q2570590"] = "Q172579"   # 意大利占领区（法国东南部）


# 名义上不属于阵营、但与之合作的附庸：阵营图层以该阵营颜色的浅色/虚线显示，不计入成员国。
# 占领区仍由 occupiers() 继承占领国的实色，与附庸虚线分开。
CLIENT = {
    "Q69808": {"bloc": "Q43056", "from": "1940-07-10", "to": "1944-08-25", "tag": "附庸（维希法国：名义中立、与轴心合作）",
               "src": "https://en.wikipedia.org/wiki/Vichy_France"},
    "Q30623": {"bloc": "Q43056", "from": "1932-03-01", "to": "1945-08-19", "tag": "附庸（满洲国，日本扶植，不是轴心签署国）",
               "src": "https://en.wikipedia.org/wiki/Manchukuo"},
    "Q696242": {"bloc": "Q43056", "from": "1940-03-30", "to": "1945-08-16", "tag": "附庸（汪精卫政权，日本扶植，不是轴心签署国）",
                "src": "https://en.wikipedia.org/wiki/Wang_Jingwei_regime"},
    "Q154401": {"bloc": "Q43056", "from": "1939-03-14", "to": "1945-05-08", "tag": "附庸（斯洛伐克共和国，德国扶植）",
                "src": "https://en.wikipedia.org/wiki/Slovak_Republic_(1939%E2%80%931945)"},
    "Q153128": {"bloc": "Q43056", "from": "1941-04-10", "to": "1945-05-08", "tag": "附庸（克罗地亚独立国）",
                "src": "https://en.wikipedia.org/wiki/Independent_State_of_Croatia"},
    "Q153660": {"bloc": "Q43056", "from": "1943-09-23", "to": "1945-04-25", "tag": "附庸（意大利社会共和国）",
                "src": "https://en.wikipedia.org/wiki/Italian_Social_Republic"},
    "Q5589262": {"bloc": "Q43056", "from": "1941-08-29", "to": "1944-10-04", "tag": "附庸（塞尔维亚救国政府）",
                 "src": "https://en.wikipedia.org/wiki/Government_of_National_Salvation"},
    "Q152750": {"bloc": "Q43056", "from": "1939-03-16", "to": "1945-05-09", "tag": "德国保护国（不是轴心签署国）",
                "src": "https://en.wikipedia.org/wiki/Protectorate_of_Bohemia_and_Moravia"},
}


def occupiers(p):
    if p.get("TERR_CAT") in ("zone_occupied", "zone_regime") and p.get("TERRITORY") in PATRON:
        return [PATRON[p["TERRITORY"]]]
    st = p.get("WW2_STATUS") or ""
    if "occupied" not in st.lower() and "annexed" not in st.lower() and "administ" not in st.lower():
        return []
    return [q for k, q in OCCUPIER_QID.items() if k in st]


MODULE = AlliancesLayer()
