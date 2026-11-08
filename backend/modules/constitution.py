"""
模块「宪法 / 基本法」。

只显示所选日期、实际解析到的政权正在施行的文本。生效日含当天，until 不含当天。
没有收录的政权不出现这一页，也不写成「无宪法」。
同一部文本可以分属不同政权的不同时段，避免把后来的宪法套到被占领区或更早的政权。
"""
from __future__ import annotations

import json

from ..registry import ContentModule
from ._state_common import pick_state


def _day(date) -> str | None:
    if not date.m or not date.d:
        return None
    return f"{date.y:04d}-{date.m:02d}-{date.d:02d}"


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
    title = "宪法"
    order = 8
    description = "所选日期该政权正在施行的宪法或基本法。没有收录时不显示这一页。"
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
        return any(_on(day, sp.get("from"), sp.get("until")) and sp.get("qid") in qids for sp in it.get("spans") or [])

    def _pack(self, it, day):
        parts = []
        for part in it.get("parts") or []:
            if not _on(day, part.get("effective"), part.get("until")):
                continue
            parts.append({
                "id": part["id"], "title": part["title_zh"], "title_orig": part.get("title_orig") or "",
                "kind": part.get("kind") or "charter", "kind_zh": self.kinds.get(part.get("kind") or "charter", "类型待考"),
                "promulgated": part.get("promulgated"), "effective": part.get("effective"),
                "summary": part.get("summary_zh") or "",
            })
        kind = it.get("kind") or "pending"
        return {
            "id": it["id"], "title": it["title_zh"], "title_en": it.get("title_orig") or "",
            "kind": kind, "kind_zh": self.kinds.get(kind, "类型待考"),
            "adopted": it.get("adopted"), "promulgated": it.get("promulgated"),
            "effective": it.get("effective"), "repealed": it.get("repealed"),
            "summary": it.get("summary_zh") or "",
            "links": [{"label": s["label"], "url": s["url"]} for s in it.get("sources") or []],
            "parts": parts,
        }

    def query(self, ctx, polity, date, params):
        empty = {"items": [], "total": 0, "shown": False, "kind": "constitution"}
        if polity is None:
            return {**empty, "note": "请在地图上点击一个国家或政权。没有点选，只是这一页还没有对象。"}
        day = _day(date)
        if not day:
            return {**empty, "note": "宪法按日比较。请把日期选到某一天。"}
        st, _alts = pick_state(ctx, polity, date, params)
        if not st:
            return {**empty, "note": "没有把这个区域对应到当时的政权。没有对应上，只说明这一条没有挂上去。"}
        qids = _acting(st, params.get("_chain"))
        hits = [self._pack(it, day) for it in self.instruments if self._hit(it, qids, day)]
        name = st.get("zh") or st.get("en") or st["id"]
        if hits:
            return {
                "items": hits, "total": len(hits), "shown": True, "kind": "constitution",
                "regime": {"id": qids[0], "name": name},
                "note": "只列出这一天正在施行的文本。通过、公布、生效和废止分开。没有写废止，就是本批没有把它记成已经废止。",
            }
        gap = next((g for g in self.gaps if any(q in (g.get("qids") or []) for q in qids) and _on(day, g.get("from"), g.get("until"))), None)
        if gap:
            return {**empty, "regime": {"id": qids[0], "name": name}, "note": gap["note"]}
        if any(q in self.covered for q in qids):
            return {**empty, "regime": {"id": qids[0], "name": name},
                    "note": "已核对该政权这一天没有正在施行的宪法或基本法条目。这是整理范围内的空档。"}
        return {**empty, "regime": {"id": qids[0], "name": name},
                "note": "当前整理范围没有收录这个政权。没有收录不等于这个政权没有自己的基本法。"}


MODULE = ConstitutionModule()
