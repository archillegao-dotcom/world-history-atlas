"""
模块「宪法 / 基本法」。

按所选日期和点到的政权列出本批已核对的文本。生效日含当天，until 不含当天。
页面上没有某部文本，只说明本批没有这条记录。
同一部文本可以分属不同政权、不同效力阶段，避免把后来的法律套到被占领区或更早的政权。
"""
from __future__ import annotations

import json

from ..registry import ContentModule
from ._state_common import pick_state


def _day(date) -> str | None:
    if not date.m or not date.d:
        return None
    return f"{date.y:04d}-{date.m:02d}-{date.d:02d}"


def _next_day(day: str) -> str:
    from datetime import date, timedelta
    y, m, d = (int(x) for x in day.split("-"))
    return (date(y, m, d) + timedelta(days=1)).isoformat()


def _on(day: str, start: str | None, end: str | None) -> bool:
    if start and day < start:
        return False
    if end and day >= end:
        return False
    return True


def _acting(st, chn) -> list[str]:
    if not st:
        return []
    now = [r for r in (chn or {}).get("now") or [] if r.get("qid") and not r.get("parallel")]
    if now:
        qids = []
        # 同一条链上可以有两个都还没写结束日的政权，例如 1949 年以后的中华人民共和国和中华民国。
        # 点到的就是其中一行时，只用这一行，避免把另一政权的宪法套过来。
        if any(r["qid"] == st["id"] for r in now):
            qids = [st["id"]]
        else:
            for r in now:
                if r["qid"] not in qids:
                    qids.append(r["qid"])
        umbrella = (chn or {}).get("country")
        if st["id"] != umbrella and st["id"] not in qids:
            qids.append(st["id"])
        return qids
    return [st["id"]]


class ConstitutionModule(ContentModule):
    id = "constitution"
    title = "宪法 / 基本法"
    order = 8
    description = "所选日期该政权已核对的宪法或基本法。没有列出不等于没有。"
    frontend = "modules/constitution.js"
    source = "见各条链接。摘要是根据公开文本写的短句，不是条文抄录。"

    def load(self, ctx):
        p = ctx.data_dir / "curated" / "constitutions.json"
        raw = json.loads(p.read_text(encoding="utf-8"))
        self.kinds = raw.get("kinds") or {}
        self.instruments = raw.get("instruments") or []
        self.gaps = raw.get("gaps") or []
        self.covered = set()
        for it in self.instruments:
            for sp in it.get("spans") or []:
                self.covered.add(sp["qid"])
        for g in self.gaps:
            self.covered.update(g.get("qids") or [])

    def stats(self):
        return {"instruments": len(self.instruments)}

    def _hit(self, it, qids, day):
        if not any(_on(day, sp.get("from"), sp.get("until")) and sp.get("qid") in qids for sp in it.get("spans") or []):
            return False
        phases = it.get("phases") or []
        if phases and not any(_on(day, ph.get("from"), ph.get("until")) for ph in phases):
            return False
        return True

    def _phase(self, it, day):
        for ph in it.get("phases") or []:
            if _on(day, ph.get("from"), ph.get("until")):
                return ph
        return None

    def _pack(self, it, day):
        parts = []
        for part in it.get("parts") or []:
            if not _on(day, part.get("effective"), part.get("until")):
                continue
            parts.append({
                "id": part["id"], "title": part["title_zh"], "title_orig": part.get("title_orig") or "",
                "kind": part.get("kind") or "charter", "kind_zh": self.kinds.get(part.get("kind") or "charter", "类型待考"),
                "promulgated": part.get("promulgated"), "effective": part.get("effective"),
                "since_note": part.get("since_note") or "",
                "summary": part.get("summary_zh") or "",
            })
        kind = it.get("kind") or "pending"
        ph = self._phase(it, day) or {}
        day_note = ""
        if it.get("promulgated") == day and it.get("day_grain"):
            day_note = it["day_grain"]
        elif it.get("promulgated") and day > it["promulgated"] and it.get("after_grain") and day <= _next_day(it["promulgated"]):
            day_note = it["after_grain"]
        return {
            "id": it["id"], "title": it["title_zh"], "title_en": it.get("title_orig") or "",
            "kind": kind, "kind_zh": self.kinds.get(kind, "类型待考"),
            "adopted": it.get("adopted"), "promulgated": it.get("promulgated"),
            "effective": it.get("effective"), "effective_clause": it.get("effective_clause"),
            "effective_clause_orig": it.get("effective_clause_orig"),
            "repealed": it.get("repealed"),
            "force_zh": ph.get("force_zh") or "", "force_note": ph.get("force_note") or "",
            "day_note": day_note,
            "summary": it.get("summary_zh") or "",
            "links": [{"label": s["label"], "url": s["url"]} for s in it.get("sources") or []],
            "parts": parts,
        }

    def query(self, ctx, polity, date, params):
        coverage = "本页只收录已核对的一部分。没有列出某部文本，只说明本批没有这条记录，不等于这个政权没有宪法或基本法。"
        base = {"items": [], "total": 0, "shown": False, "kind": "constitution", "coverage": coverage}
        if polity is None:
            return {**base, "note": "请在地图上点击一个国家或政权。"}
        day = _day(date)
        if not day:
            return {**base, "shown": True, "note": "这一页按日比较。请把日期选到某一天。"}
        st, _alts = pick_state(ctx, polity, date, params)
        if not st:
            return {**base, "shown": True, "note": "没有把这个区域对应到当时的政权。没有对应上，只说明这一条没有挂上去。"}
        qids = _acting(st, params.get("_chain"))
        hits = [self._pack(it, day) for it in self.instruments if self._hit(it, qids, day)]
        name = st.get("zh") or st.get("en") or st["id"]
        head = {"shown": True, "kind": "constitution", "coverage": coverage, "regime": {"id": qids[0], "name": name}}
        if hits:
            return {**head, "items": hits, "total": len(hits),
                    "note": "通过、公布、生效和废止分开写。效力一栏写的是形式地位和实际状态，两者可以不同。"}
        gap = next((g for g in self.gaps if any(q in (g.get("qids") or []) for q in qids) and _on(day, g.get("from"), g.get("until"))), None)
        if gap:
            return {**head, "items": [], "total": 0, "note": gap["note"]}
        if any(q in self.covered for q in qids):
            return {**head, "items": [], "total": 0,
                    "note": "已核对该政权这一天没有正在列出的条目。这是整理范围内的空档。"}
        return {**head, "items": [], "total": 0,
                "note": "当前整理范围没有收录这个政权。"}


MODULE = ConstitutionModule()
