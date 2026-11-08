"""
政权解析：地图多边形（快照, fid）+ 日期 → Wikidata 政权。

数据：
  data/polity_map.json.gz  每个多边形的候选政权（名称匹配 / 首都在多边形内 / 自身坐标在内），见 tools/build_polity_map.py
  data/states.json.gz      政权详情（存在期、首都、政体、元首、首脑……）
  data/offices.json.gz     职位与任职者；data/persons.json.gz 人物；data/orgs.json.gz 机构

resolve() 返回所选日期「存在」的候选（存在期包含该日期；缺失的端点视为开放），按分数排序。
第一个作为「主要政权」，其余作为「同一地区当时的其他政权」供用户切换。
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from .datafile import read_json
from .timeutil import HDate, rec_key


def _load(path: Path, default):
    return read_json(path, default)


def valid_at(dk: float, a: dict | None, b: dict | None, slack: float = 0.0) -> bool:
    ka, kb = rec_key(a), rec_key(b)
    return (ka is None or ka - slack <= dk) and (kb is None or dk <= kb + slack)


STRONG = {"cshapes", "curated-name", "ww2", "dynasty", "naturalearth", "wiki-title", "name", "capital+name", "coord+name", "predecessor", "successor", "territory"}
NOW_KEY = 2100.0


def _slack(t: dict | None) -> float:
    """只精确到年（或更粗）的端点允许 1 年误差；精确到月/日的端点不放宽。"""
    return 1.0 if t and not t.get("m") else 0.0


OPEN_END_YEARS = 50   # 起始年早于 1800、没有任何终止信息的政权：只在起始后 50 年内作为候选（不猜测它延续多久）


def lifespan(s: dict) -> tuple:
    """政权存在期 (起, 止, 说明)。起止优先用 P571/P576；缺失时用该政权各条带时间的语句（首都、元首、政体）中
    最早的开始 / 最晚的结束（P580/P582）。仍不知道起始时间的政权视为「存在期未知」，不作为地图候选
    （除非在 data/curated 中明确列出）。"""
    if "_life" in s:
        return s["_life"]
    a, b, note = s.get("from"), s.get("to"), None
    if a is None or b is None:
        subs = [x for f in ("capitals", "hos", "hog", "gov") for x in s.get(f, [])]
        if a is None:
            st = [x["from"] for x in subs if x.get("from")]
            if st:
                a = min(st, key=rec_key)
                note = "起始时间取自最早的带时间语句"
        if b is None and s.get("from") is None:
            en = [x["to"] for x in subs if x.get("to")]
            if en:
                b = max(en, key=rec_key)
    if a is not None and b is None and rec_key(a) < 1800 and not s.get("curated") and not s.get("current"):
        b = {"y": a["y"] + OPEN_END_YEARS, "m": 0, "d": 0, "p": 9}
        note = f"Wikidata 未记录终止时间，只在起始后 {OPEN_END_YEARS} 年内显示"
    s["_life"] = (a, b, note)
    return s["_life"]


def alive(dk: float, s: dict) -> bool:
    a, b, _ = lifespan(s)
    if a is None and not s.get("curated"):
        return False   # 存在期未知：不作为候选（避免「仲家」这类条目出现在商代）
    ka, kb = rec_key(a), rec_key(b)
    if dk >= 1800:
        # 1800 年以后：只精确到年的端点按「该年 1 月 1 日 / 12 月 31 日」理解，不再放宽一年
        # （否则 1959 年的尼日尔、1989 年的纳米比亚会在独立前就显示为独立国家）
        if a is not None and not a.get("m"):
            ka = float(a["y"])
        if b is not None and not b.get("m"):
            kb = float(b["y"]) + 0.999
        return (ka is None or ka <= dk) and (kb is None or dk <= kb)
    return (ka is None or ka - _slack(a) <= dk) and (kb is None or dk <= kb + _slack(b))


class PolityResolver:
    def __init__(self, data_dir: Path):
        self.map = _load(data_dir / "polity_map.json.gz", {})
        self.states = {s["id"]: s for s in _load(data_dir / "states.json.gz", [])}
        # 整理数据引用、但 states.json 没有的政权条目（占领当局、傀儡政权等；tools/build_runtime_states.py 从 Wikidata 取得）
        _rs = data_dir / "curated" / "runtime_states.json"
        if _rs.exists():
            for q, r in json.loads(_rs.read_text(encoding="utf-8")).items():
                if q.startswith("Q") and q not in self.states:
                    # 只由带起止日期的整理图层（控制区、二战按月边界、CShapes 分期）引用：存在期以图层日期为准，Wikidata 缺起止也可作候选
                    self.states[q] = {**r, "curated": True}
        # 微型国家、虚构国家/地点等不是历史政权的条目（tools/build_state_exclusions.py 由 Wikidata 类别生成）：从候选中去掉
        _ex = data_dir / "curated" / "state_exclusions.json"
        self.excluded = {}
        if _ex.exists():
            _exd = json.loads(_ex.read_text(encoding="utf-8"))
            for q, why in _exd.get("exclude", {}).items():
                st = self.states.get(q)
                hard = {"微型国家", "虚构国家", "虚构地点"} & set(why)
                if st is not None and (hard or ("虚构实体" in why and not st.get("from"))):
                    self.excluded[q] = why
                    del self.states[q]
        # 人工核对的存在期修正（data/curated/lifespan_overrides.json，每条注明来源）
        _lo = data_dir / "curated" / "lifespan_overrides.json"
        if _lo.exists():
            for q, r in json.loads(_lo.read_text(encoding="utf-8")).items():
                st = self.states.get(q)
                if not st or q.startswith("_"):
                    continue
                for k in ("from", "to"):
                    if k in r:
                        st[f"wd_{k}"] = st.get(k)
                        st[k] = r[k]
                if r.get("zh"):   # 面板显示名（Wikidata 中文标签指今天的行政区时，如「柔佛州」）
                    st["wd_zh"], st["zh"] = st.get("zh"), r["zh"]
                if r.get("current"):   # 至今仍存在（如今马来西亚各州的苏丹国）：没有终止时间是正常的
                    st["current"] = True
                st["curated_note"] = ((st.get("curated_note") or "") + " " + r["note"]).strip()
                st["sources"] = st.get("sources", []) + r.get("sources", [])
        self.offices = _load(data_dir / "offices.json.gz", [])
        self.persons = {p["id"]: p for p in _load(data_dir / "persons.json.gz", [])}
        _ps = data_dir / "curated" / "person_supplements.json"
        if _ps.exists():
            for q, r in json.loads(_ps.read_text(encoding="utf-8")).items():
                if q.startswith("_"):
                    continue
                self.persons.setdefault(q, {"id": q})
                self.persons[q].update({k: v for k, v in r.items() if k != "src"})
                if r.get("src"):
                    self.persons[q]["sources"] = self.persons[q].get("sources", []) + [r["src"]]
        self.orgs = {o["id"]: o for o in _load(data_dir / "orgs.json.gz", [])}
        # 中文名补译（data/curated/zh_labels.json：Wikidata 中文标签 / 中文维基条目名）
        from .zh import fill as _zh_fill
        for _recs in (self.states.values(), self.persons.values(), self.offices, self.orgs.values()):
            _zh_fill(_recs, data_dir)
        # 现代仍存在的政权/领土（Natural Earth 2011 快照自带的 QID、特殊地位领土）：没有终止时间是正常的
        for fid, cs in self.map.get("2011", {}).items():
            for q, m, _ in cs:
                if m == "naturalearth" and q in self.states:
                    self.states[q]["current"] = True
        _tq = data_dir / "territory_qids.json"
        self.territory_qids = set(json.loads(_tq.read_text(encoding="utf-8"))) if _tq.exists() else set()
        if _tq.exists():
            for q in json.loads(_tq.read_text(encoding="utf-8")):
                if q in self.states and not self.states[q].get("to"):
                    self.states[q]["current"] = True
        # 交叉核对（tools/xcheck_seshat.py）：Seshat 与 Wikidata 存在期不一致的政权，在面板中注明 Seshat 的年份
        _xp = data_dir / "xcheck" / "seshat.json"
        if _xp.exists():
            for q, r in json.loads(_xp.read_text(encoding="utf-8")).get("records", {}).items():
                if q in self.states:
                    st = self.states[q]
                    st["xcheck"] = r
                    if r["status"] == "conflict":
                        yz = lambda y: "?" if y is None else (f"前{-y}" if y < 0 else str(y))
                        st["xcheck_note"] = (f"交叉核对：Seshat 全球历史数据库记为 {yz(r['seshat'][1])}–{yz(r['seshat'][2])} 年"
                                             f"（「{r['seshat'][0]}」各阶段合计），与 Wikidata 的 {yz(r['wikidata'][0])}–{yz(r['wikidata'][1])} 年"
                                             f"不一致（Seshat 只统计其 35 个采样区域内的阶段，结束年份常早于政权实际结束）；地图仍按 Wikidata 显示。")
        # 名称匹配排除表（data/curated/match_block.json）：底图名称 → 不应匹配的政权
        _mb = data_dir / "curated" / "match_block.json"
        self.match_block = {k: set(v["block"]) for k, v in json.loads(_mb.read_text(encoding="utf-8")).items()
                            if not k.startswith("_")} if _mb.exists() else {}
        # 中国地区朝代时间轴（data/curated/china_dynasties.json）
        _dp = data_dir / "curated" / "china_dynasties.json"
        self.dyn = json.loads(_dp.read_text(encoding="utf-8")) if _dp.exists() else {}
        for q, n in self.dyn.get("notes", {}).items():
            if q in self.states:
                self.states[q]["curated_note"] = n
        # 君主/统治者补充（tools/build_rulers.py）：带 P1001 限定的任职记录组成的「虚拟职位」与年号
        ru = _load(data_dir / "rulers.json.gz", {}) or {}
        self.offices = self.offices + ru.get("offices", [])
        for p in _load(data_dir / "ruler_persons.json.gz", []) or []:
            self.persons.setdefault(p["id"], p)
        # 中国皇帝（Q268218）缺管辖区的任职记录补到当时的主朝代（tools/build_china_emperor_fill.py）
        fl = _load(data_dir / "ruler_fills.json.gz", {}) or {}
        for p in fl.get("persons", []):
            self.persons.setdefault(p["id"], p)
        # 君主补充数据载入后再补译一次（已有中文的不动）
        for _recs in (self.persons.values(), self.offices):
            _zh_fill(_recs, data_dir)
        _ob = {o["id"]: o for o in self.offices}
        self.n_ruler_fills = 0
        for f in fl.get("fills", []):
            o = _ob.get(f["office"])
            if o is None:
                o = {"id": f["office"], "pos": "Q268218", "juris": [f["state"]], "virtual": True, "zh": "中国皇帝",
                     "en": "Emperor of China", "desc": "中国历代皇帝", "sl": 43, "juris_zh": f.get("state_zh"), "holders": []}
                self.offices.append(o)
                _ob[o["id"]] = o
            if not any(h["p"] == f["p"] and h.get("from") == f["from"] for h in o["holders"]):
                o["holders"] = o["holders"] + [{"p": f["p"], "from": f["from"], "to": f["to"], "src": f["source"]}]
                self.n_ruler_fills += 1
        # 错配任职记录的人工剔除（data/curated/ruler_blocks.json）
        _bp = data_dir / "curated" / "ruler_blocks.json"
        if _bp.exists():
            for oid, ps in json.loads(_bp.read_text(encoding="utf-8")).items():
                if oid in _ob:
                    _ob[oid]["holders"] = [h for h in _ob[oid]["holders"] if h["p"] not in ps]
        self.eras_by_state: dict[str, list[dict]] = {}
        for e in ru.get("eras", []):
            self.eras_by_state.setdefault(e["state"], []).append(e)
        self.office_by_state: dict[str, list[dict]] = {}
        for o in self.offices:
            for s in o.get("juris", []):
                self.office_by_state.setdefault(s, []).append(o)
        # 职位补充管辖政权（data/curated/office_links.json）
        _ol = data_dir / "curated" / "office_links.json"
        if _ol.exists():
            for oid, r in json.loads(_ol.read_text(encoding="utf-8"))["links"].items():
                o = _ob.get(oid)
                for s in (r["states"] if o else []):
                    if o not in self.office_by_state.setdefault(s, []):
                        self.office_by_state[s].append(o)
        # 补充职位：与名义君主并立的实际掌权者（幕府将军、摄政/关白、执权、护国公；data/curated/extra_offices.json，
        # tools/curated_src/extra_offices.py 从 Wikidata 取任职记录）。同一职位原有的零散记录由完整记录取代。
        _xo = data_dir / "curated" / "extra_offices.json"
        if _xo.exists():
            for r in json.loads(_xo.read_text(encoding="utf-8"))["offices"]:
                for h in r["holders"]:
                    if h["p"] not in self.persons:
                        self.persons[h["p"]] = {"id": h["p"], "zh": h.get("zh"), "en": h.get("en")}
                o = {"id": r["id"] + "@extra", "pos": r["id"], "zh": r["zh"], "en": None, "desc": r["note"], "sl": 60,
                     "juris": r["juris"], "holders": [{"p": h["p"], "from": h["from"], "to": h["to"]} for h in r["holders"] if h.get("from")],
                     "sources": [{"name": f"Wikidata {r['id']} 的 P39 任职声明（起止限定）", "url": r["src"]}]}
                self.offices.append(o)
                _ob[o["id"]] = o
                for s in r["juris"]:
                    lst = [x for x in self.office_by_state.get(s, []) if x.get("pos") != r["id"] and x["id"] != r["id"]]
                    self.office_by_state[s] = lst + [o]
            # 补充任职记录（Wikidata 缺漏、据史书补的个别君主；每条注明来源）
            for h in json.loads(_xo.read_text(encoding="utf-8")).get("extra_holders", []):
                o = _ob.get(h["office"])
                if o is None:
                    continue
                if h["p"] not in self.persons:
                    self.persons[h["p"]] = {"id": h["p"], "zh": h.get("zh")}
                o["holders"] = o.get("holders", []) + [{"p": h["p"], "from": h["from"], "to": h["to"], "note": h.get("note"), "src": h.get("src")}]
        # 底图名称的人工候选（data/curated/name_candidates.json）
        _nc = data_dir / "curated" / "name_candidates.json"
        _ncd = json.loads(_nc.read_text(encoding="utf-8")) if _nc.exists() else {}
        self.name_cands = _ncd.get("names", {})
        self.name_cands_ww2 = _ncd.get("ww2_before", {}).get("list", [])
        # 朝代起止只精确到年时，用该朝「中国皇帝」任职记录中精确到日的首任开始 / 末任结束细化（同一年内），
        # 避免 1644 年 7 月仍显示已亡的明朝而没有在位君主（末任结束早于朝代止年的年中）
        for q in self.dyn.get("main", []) + self.dyn.get("secondary", []):
            st = self.states.get(q)
            if not st:
                continue
            hs = [h for o in self.office_by_state.get(q, []) if o.get("pos") == "Q268218" for h in o.get("holders", [])]
            a, b, note = lifespan(st)
            a2, b2 = a, b
            if a and not a.get("m"):
                fr = [h["from"] for h in hs if h.get("from") and h["from"].get("m") and h["from"]["y"] == a["y"]]
                if fr:
                    a2 = min(fr, key=rec_key)
            if b and not b.get("m"):
                to = [h["to"] for h in hs if h.get("to") and h["to"].get("m") and h["to"]["y"] == b["y"]]
                if to and all(not (h.get("to") and rec_key(h["to"]) > rec_key(max(to, key=rec_key))) for h in hs if h.get("to")):
                    b2 = max(to, key=rec_key)
            if (a2, b2) != (a, b):
                st["_life"] = (a2, b2, (note + "；" if note else "") + "起止细化到首任/末任君主的任职日期")
        # 官方历任名单（tools/build_official_offices.py）：补 Wikidata 缺失的任职者/任期，每条记录注明来源网址
        from .official import merge as _merge_official
        self.official_stats = _merge_official(self, data_dir)

    # ------------------------------------------------------------------ 解析
    geo = None  # BasemapStore（由 modules/_state_common.resolver 注入），用于「首都在哪个多边形里」的判断

    def candidates(self, snap: int, fid: int) -> list[list]:
        """候选列表。过渡快照（见 backend/transitions.py）中的多边形取其来源快照的候选。"""
        if self.geo is not None:
            snap, fid = self.geo.origin(snap, fid)
            if snap == "terr":   # 特殊地位领土：候选为该领土条目及其前身（P1365 链）
                t = self.geo.trans.terr[fid]
                return [[q, "territory", 150 - k] for k, q in enumerate(t.get("chain", []))]
            if snap == "cs":     # CShapes 行：整理好的分期（带起止日期）> Natural Earth 现代 QID > 名称匹配；殖民地另加宗主国
                return self._cs_cands(fid)
            if snap == "q":      # 战线切出的占领区/解放区：直接给出政权 QID
                return [[fid, "ww2", 600]]
            if snap == "ww2":    # Stanford 二战按月边界的要素
                md, kk = fid
                W = self.geo.cs.war
                nm, st = W.stan_feats(md)[kk][1][:2]
                out = []
                for c in W.stan_cands(nm, st, None):
                    if c[0] == "gw":
                        out += self._cs_gw_cands(c[1], None, None)
                    else:
                        out.append(c)
                # 快照月内才成立的政权：成立日以前改用前身（name_candidates.json 的 ww2_before）
                for q_new, q_old, a, b, _ in self.name_cands_ww2:
                    if any(c[0] == q_new for c in out):
                        out = [([q_new, c[1], c[2], b, None] if c[0] == q_new and len(c) == 3 else c) for c in out]
                        out.insert(0, [q_old, "ww2", 700, a, b])
                return out
            if snap == "csx":    # 补充的微型国家 / 小岛国
                e = self.geo.cs.extras[fid]
                return [[e["qid"], "cshapes", 600, e.get("from"), e.get("to")]]
        base = self.map.get(str(snap), {}).get(str(fid), [])
        # 下级行政区（build_states.py 标记 sub，如「墨西哥州」）只在 Natural Earth 自带其 ID 时作为候选
        base = [c for c in base if c[1] == "naturalearth" or not (self.states.get(c[0]) or {}).get("sub")
                or c[0] in self.territory_qids]
        if self.match_block and self.geo is not None:
            f = self.geo.polity(snap, fid)
            blk = self.match_block.get((f or {}).get("props", {}).get("NAME"))
            if blk:
                base = [c for c in base if c[0] not in blk]
        if self.name_cands and self.geo is not None:
            f = self.geo.polity(snap, fid)
            nc = self.name_cands.get((f or {}).get("props", {}).get("NAME"))
            if nc:
                base = [[q, "curated-name", 550, a, b] for q, a, b, _ in nc] + base
        return self._dynasty(snap, fid) + base

    def _cs_cands(self, i) -> list:
        r = self.geo.cs.rows[i]
        return self._cs_gw_cands(r["gw"], r["status"], r.get("owner"))

    def _cs_gw_cands(self, gw, status, owner) -> list:
        cs = self.geo.cs
        r = {"gw": gw, "status": status or "independent", "owner": owner}
        gi = cs.gw.get(r["gw"], {})
        out = [[q, "cshapes", 600, a, b] for a, b, q in gi.get("periods", [])]
        if gi.get("ne"):
            out.append([gi["ne"][0], "name", 320])
        out += [[q, "name", 300] for q in gi.get("names", []) if not (self.states.get(q) or {}).get("sub")]
        if r.get("owner") and r["status"] != "independent":
            og = cs.gw.get(r["owner"], {})
            for a, b, q in og.get("periods", []):
                out.append([q, "owner", 90, a, b])
            if og.get("ne"):
                out.append([og["ne"][0], "owner", 80])
            out += [[q, "owner", 70] for q in og.get("names", [])]
        return out

    def _dynasty(self, snap, fid) -> list:
        """中国地区多边形：按名称加入朝代候选（method="dynasty"，分数越高越优先）。"""
        if not self.dyn or self.geo is None or not isinstance(snap, int):
            return []
        lo, hi = self.dyn.get("range", [-2200, 1949])
        if not lo <= snap <= hi:
            return []
        f = self.geo.polity(snap, fid)
        pname = f["props"].get("NAME") if f else None
        # 底图拼写 Zhoa / Zhou states 是周，不是商。若套用整份「main」朝代，前1046年以前西周尚未开始，
        # 这块会和 Sinic 一起落到商朝，看起来像两个商。这里只给周的条目，并用底图快照的年份撑住候选，
        # 避免再沿「取代了商」退回商朝。周灭商的学术年代仍约前1046年，传统纪年（约前1122年）不是依据。
        # https://en.wikipedia.org/wiki/Western_Zhou
        # https://en.wikipedia.org/wiki/Xia%E2%80%93Shang%E2%80%93Zhou_Chronology_Project
        if pname in ("Zhoa", "Zhou states"):
            return [
                ["Q1069609", "dynasty", 480, -15000101, -7710101],
                ["Q307066", "dynasty", 470, -7710101, -2560101],
                ["Q35216", "dynasty", 460, -10460101, -2560101],
            ]
        grp = self.dyn["names"].get(pname) if pname else None
        if not grp:
            return []
        order = (self.dyn["main"] + self.dyn["secondary"]) if grp == "main" else (grp + self.dyn["main"] + self.dyn["secondary"])
        seen, out = set(), []
        for k, q in enumerate(order):
            if q not in seen:
                seen.add(q)
                out.append([q, "dynasty", 400 - k])
        return out

    def _dyn_ruler(self, q, dk):
        """朝代 q 在 dk 是否有在位的「中国皇帝」（前后 0.25 年内）；没有该朝的皇帝任职记录时返回 None。"""
        hs = [h for o in self.office_by_state.get(q, []) if o.get("pos") == "Q268218" for h in o.get("holders", [])]
        if not hs:
            return None
        for h in hs:
            a, b = rec_key(h.get("from")), rec_key(h.get("to"))
            if (a is None or a - 0.25 <= dk) and (b is None or dk <= b + 0.25):
                return True
        return False

    @staticmethod
    def capital_at(s: dict, dk: float):
        """该政权在 dk 时的首都坐标（有起止时间的取包含 dk 的那条；都没有时间时取首选/唯一的一条）。"""
        caps = [c for c in s.get("capitals", []) if c.get("coord")]
        dated = [c for c in caps if (c.get("from") or c.get("to")) and valid_at(dk, c.get("from"), c.get("to"))]
        if dated:
            return dated[-1]["coord"]
        und = [c for c in caps if not c.get("from") and not c.get("to")]
        und.sort(key=lambda c: not c.get("pref"))
        return und[0]["coord"] if und else None

    def _seat_fid(self, snap, s, dk):
        """政权在 dk 时的首都落在快照 snap 的哪个多边形里（没有首都坐标或落在海上时返回 None）。"""
        if self.geo is None:
            return None
        co = self.capital_at(s, dk)
        if not co:
            return None
        f = self.geo.locate(snap, co[0], co[1])
        return f["props"]["fid"] if f else None

    def resolve(self, snap: int, fid: int, date: HDate, min_score: float = 0) -> list[dict]:
        """所选日期存在的候选政权，排序规则：
        1. 「强」候选（Natural Earth 自带 ID、同名维基条目、名称匹配、首都在内且名称相近）在前；
        2. 已被另一个同时存在的候选「取代」（P1366）的政权排在取代者之后（如 1949-10-01 以后的
           「中华民国(1912–1949)」排在「中华人民共和国」之后）；
        3. 强候选中 Natural Earth 优先，其余按存在期由短到长——同一地区同名的多个政权里，
           存在期最短且包含该日期的通常就是当时那个具体政权（如 1938 年的「纳粹德国」而不是「德国」）；
        4. 弱候选（仅首都/坐标落在范围内，常是下级行政区）按分数排在后面。
        「另有所在」降级：仅靠名称匹配的候选，如果它当时的首都落在本快照的**另一个**多边形里，而本多边形还有
        别的强候选，就降为弱候选（例：1949 年 12 月以后首都在台北的「中华民国」不再作为中国大陆多边形的强候选；
        首都在汉城的「大韩民国」不作为朝鲜北半部的强候选）。
        前身/继承：若没有任何强候选在该日期存在，则沿 Wikidata「取代了」(P1365)/「被取代」(P1366) 找当时存在的
        前身或继承政权（继承政权要求首都在本多边形内）。"""
        dk = date.key()
        k8 = date.y * 10000 + (date.m or 1) * 100 + (date.d or 1)
        out, raw = [], []
        for cand in self.candidates(snap, fid):
            qid, method, score = cand[:3]
            s = self.states.get(qid)
            if not s or score < min_score:
                continue
            if len(cand) > 3:   # 带整理好的起止日期（CShapes 分期）：以分期为准，不再看 Wikidata 存在期
                a, b = cand[3], cand[4]
                if isinstance(a, str):
                    a = int(a.replace("-", "")) if a else None
                if isinstance(b, str):
                    b = int(b.replace("-", "")) if b else None
                if (a is None or a <= k8) and (b is None or k8 < b):
                    out.append({"state": s, "method": method, "score": score, "strong": method in STRONG, "period": [a, b]})
                continue
            raw.append((s, method, score))
            if alive(dk, s):
                out.append({"state": s, "method": method, "score": score, "strong": method in STRONG})
        # 当天已有整理过分期时，去掉「名称匹配」到另一个政权的候选。
        # 否则继任者（如日治台湾 Q137816 的 replaced_by = 中华民国 Q865，英文名恰好是 Taiwan）
        # 会因 superseded() 排到分期政权前面，1941 年的台湾被显示成中华民国。朝鲜日治时期同理。
        active_periods = {c["state"]["id"] for c in out if c.get("period")}
        if active_periods:
            out = [c for c in out if c["method"] != "name" or c["state"]["id"] in active_periods]
        if not any(c["strong"] for c in out):
            seen = {c["state"]["id"] for c in out}
            for s, method, score in raw:
                if method not in STRONG:
                    continue
                ka, kb = rec_key(s.get("from")), rec_key(s.get("to"))
                links = []
                if ka is not None and dk < ka:
                    links = [("predecessor", x["v"]) for x in s.get("replaces", [])]
                elif kb is not None and dk > kb:
                    links = [("successor", x["v"]) for x in s.get("replaced_by", [])]
                for how, q in links:
                    t = self.states.get(q)
                    if not t or q in seen or not alive(dk, t):
                        continue
                    sf = self._seat_fid(snap, t, dk)
                    if how == "successor" and sf != fid:
                        continue
                    if how == "predecessor" and sf is not None and sf != fid:
                        continue   # 前身政权的首都在别的多边形里（如 1492 年「日本」多边形的前身链指向琉球）
                    seen.add(q)
                    out.append({"state": t, "method": how, "score": score - 5, "strong": True, "via": s["id"]})
            # 已分裂：同一个已解散政权有多个继承政权的首都都在这个多边形里（如 476 年后的西罗马帝国、1171 年后的法蒂玛王朝）。
            # 底图几何要到下一张快照才更新，此时不能把整个旧范围交给其中一个继承者 → 全部降为弱候选并标记 split
            succ = [c for c in out if c["method"] == "successor"]
            if len({c["state"]["id"] for c in succ}) > 1:
                for c in succ:
                    c["strong"] = False
                    c["split"] = True
        strong_ids = {c["state"]["id"] for c in out if c["strong"]}
        if len(strong_ids) > 1:
            # 名称匹配的候选：首都在另一个多边形里时降为弱候选（只在降级后仍有强候选时执行）。
            # 朝代候选不做此降级：蒙古帝国等首都在别处的大帝国会因此被错误降级（已测试：1220–1250 年北京变成「东辽国」）
            far = []
            for c in out:
                if c["strong"] and c["method"] == "name":
                    sf = self._seat_fid(snap, c["state"], dk)
                    if sf is not None and sf != fid:
                        far.append((c, sf))
            if len(strong_ids) > len({c["state"]["id"] for c, _ in far}):
                for c, sf in far:
                    c["strong"] = False
                    c["elsewhere"] = sf

        def span(c):
            a, b = rec_key(c["state"].get("from")), rec_key(c["state"].get("to"))
            return (b if b is not None else NOW_KEY) - (a if a is not None else -1e5)

        strong_ids = {c["state"]["id"] for c in out if c["strong"]}

        def superseded(c):
            # 被一个同时存在、且成立时间更晚的强候选取代（如 1949-10 以后的「中华民国(1912–1949)」→ 中华人民共和国）。
            # 成立时间更早的「取代者」不算（Wikidata 中「法兰西王国」P1366 含「法国」(481 年起)，但 1500 年应显示法兰西王国）
            a0 = rec_key(c["state"].get("from"))
            for x in c["state"].get("replaced_by", []):
                if x["v"] in strong_ids:
                    t = self.states.get(x["v"]) or {}
                    ta = rec_key(t.get("from"))
                    if a0 is None or ta is None or ta > a0:
                        return True
            return False

        mrank = {"cshapes": -1, "curated-name": -1, "ww2": -2, "naturalearth": 0, "dynasty": 1, "territory": 1, "predecessor": 3, "successor": 3, "owner": 5}

        def within(c):
            if c["method"] == "dynasty" and self._dyn_ruler(c["state"]["id"], dk) is False:
                return -c["score"] + 300   # 该朝此时没有在位君主（如 581–587 年仍存续的后梁）：让位给有君主的朝代
            if c["method"] in ("dynasty", "territory", "cshapes", "owner", "ww2", "curated-name"):
                return -c["score"]
            if c["method"] in ("predecessor", "successor"):
                return -c["state"].get("sl", 0)     # 多个前身/继承政权时取最主要的（维基语言版本最多）
            return span(c)
        out.sort(key=lambda c: (not c["strong"], c["strong"] and c["method"] not in ("dynasty", "territory") and superseded(c),
                                mrank.get(c["method"], 2), within(c) if c["strong"] else 0, -c["score"]))
        # 同一政权只保留一次（朝代候选与名称匹配可能重复）
        seen, uniq = set(), []
        for c in out:
            if c["state"]["id"] not in seen:
                seen.add(c["state"]["id"])
                uniq.append(c)
        out = uniq
        return out

    @staticmethod
    def primary(cands: list[dict], date: HDate):
        """主要政权：第一个强候选；1800 年以后没有强候选时，允许「首都位于此范围」的政权——但只在首都落在此范围内的
        政权只有一个时（多个时说明旧多边形已分裂成几个国家，如 1825 年后的秘鲁总督区含智利、秘鲁、玻利维亚的首都）。"""
        p = next((c for c in cands if c["strong"]), None)
        if p is None:   # CShapes 殖民地/保护国：本身没有对应的 Wikidata 条目时，显示宗主国（标签注明地位）
            p = next((c for c in cands if c["method"] == "owner"), None)
        if p is None and date.y >= 1800:
            caps = [c for c in cands if c["method"] == "capital"]
            if len({c["state"]["id"] for c in caps}) == 1:
                p = caps[0]
        return p

    @staticmethod
    def split_names(cands: list[dict]) -> list[str]:
        """多边形已分裂时的继承/首都在内的政权名（用于标签说明）。"""
        sp = [c for c in cands if c.get("split")]
        if not sp:
            caps = [c for c in cands if c["method"] == "capital"]
            sp = caps if len({c["state"]["id"] for c in caps}) > 1 else []
        out = []
        for c in sp:
            n = c["state"].get("zh") or c["state"].get("en")
            if n and n not in out:
                out.append(n)
        return out

    def strong(self, snap: int, fid: int, date: HDate) -> list[dict]:
        return [c for c in self.resolve(snap, fid, date) if c["strong"]]

    def state_name(self, qid: str) -> str:
        s = self.states.get(qid) or self.persons.get(qid) or {}
        n = s.get("zh") or s.get("en")
        if not n or (n.startswith("Q") and n[1:].isdigit()):
            return "暂无通用译名"
        from .zh import disp
        return disp(n) or "暂无通用译名"

    def person_brief(self, pid: str) -> dict:
        p = self.persons.get(pid, {})
        from .zh import disp
        shown = disp(p.get("zh") or p.get("en"))
        if not shown or (shown.startswith("Q") and shown[1:].isdigit()):
            shown = "姓名未记录"
        return {"id": pid, "name": shown, "en": p.get("en"), "desc": p.get("desc"),
                "born": p.get("born"), "died": p.get("died")}


