"""外交 / 国际组织。

按所选日期列出这一批已经核对的组织，并给出当时的资格。
名单写明不完整时，没有出现的国家不写成「不是会员」。
"""
from __future__ import annotations

import json

from ..registry import ContentModule
from ._state_common import pick_state, resolver

_ENDED = {
    "withdraw": "已退出",
    "expel": "被开除",
    "replaced": "不再持有这一席位",
    "gap": "席位待考",
}


def view_day(date) -> tuple[str, str]:
    if date.m and date.d:
        return f"{date.y:04d}-{date.m:02d}-{date.d:02d}", ""
    if date.m:
        return f"{date.y:04d}-{date.m:02d}-01", "没有选日，按该月1日显示。"
    return f"{date.y:04d}-07-01", "没有选月日，按该年7月1日显示。"


def _on(day: str, start: str | None, end: str | None) -> bool:
    if start and day < start:
        return False
    if end and day >= end:
        return False
    return True


def _alive(org: dict, day: str) -> bool:
    return _on(day, org.get("from"), org.get("until"))


def _hq(org: dict, day: str) -> str:
    for row in org.get("headquarters") or []:
        if _on(day, row.get("from"), row.get("until")):
            return row.get("text") or ""
    rows = org.get("headquarters") or []
    return rows[-1]["text"] if rows else ""


def _status(m: dict, day: str) -> str | None:
    if m.get("track") == "year":
        year = m.get("year_listed")
        if not year:
            return None
        if day < f"{int(year):04d}-01-01":
            return "按年名单尚未加入"
        return "加入日未核"
    start = m.get("from")
    if not start:
        return None
    if day < start:
        if m.get("hide_before"):
            return None
        return "尚未加入"
    uf, uu = m.get("uncertain_from"), m.get("uncertain_until")
    if uf and uu and uf <= day <= uu:
        return "通知期满的日子各说来源不一致"
    until = m.get("until")
    if until and day >= until:
        return _ENDED.get(m.get("how"), "已结束")
    if m.get("track") == "founding":
        return "签署方，后来的会籍未核"
    notice = m.get("notice")
    if notice and day >= notice:
        return "已宣布退出，通知期未满"
    return m.get("role") or "成员国"


def _view_status(org: dict, day: str) -> str:
    if not _alive(org, day):
        return "所选日期这一组织尚未成立或已经停止"
    eff = org.get("effective")
    if eff and day < eff:
        return "已签署，尚未生效"
    return "存续"


class Diplomacy:
    def __init__(self, orgs: list[dict]):
        self.orgs = orgs
        self.by_id = {o["id"]: o for o in orgs}

    def _name(self, ctx, m: dict, day: str) -> str:
        if m.get("name"):
            return m["name"]
        R = resolver(ctx)
        chosen = m.get("qid")
        for row in m.get("names") or []:
            if _on(day, row.get("from"), row.get("until")):
                chosen = row["qid"]
                break
        return R.state_name(chosen) if chosen else "名称未记录"

    def _row(self, ctx, org: dict, m: dict, day: str) -> dict:
        return {
            "qid": m.get("qid"),
            "name": self._name(ctx, m, day),
            "status": _status(m, day),
            "from": m.get("from"),
            "notice": m.get("notice"),
            "until": m.get("until"),
            "year_listed": m.get("year_listed"),
            "note": m.get("note") or "",
            "match": m.get("match") or ([m["qid"]] if m.get("qid") else []),
        }

    def brief(self, org: dict, day: str) -> dict:
        return {
            "id": org["id"], "zh": org["zh"], "en": org.get("en") or "",
            "type": org.get("type"), "type_zh": org.get("type_zh") or "",
            "from": org.get("from"), "until": org.get("until"),
            "signed": org.get("signed"), "effective": org.get("effective"),
            "view_status": _view_status(org, day),
            "headquarters": _hq(org, day),
            "incomplete": bool(org.get("incomplete")),
            "summary": org.get("summary") or "",
        }

    def alive(self, day: str) -> list[dict]:
        return [self.brief(o, day) for o in self.orgs if _alive(o, day)]

    def detail(self, ctx, oid: str, day: str) -> dict | None:
        org = self.by_id.get(oid)
        if not org:
            return None
        members = []
        for m in org.get("members") or []:
            row = self._row(ctx, org, m, day)
            if row["status"]:
                members.append(row)
        order = {
            "成员国": 0, "会商国": 0, "中国席位": 0,
            "已宣布退出，通知期未满": 1,
            "通知期满的日子各说来源不一致": 2,
            "签署方，后来的会籍未核": 3,
            "按年名单尚未加入": 4, "尚未加入": 4, "加入日未核": 4,
            "已退出": 5, "被开除": 5, "不再持有这一席位": 5, "席位待考": 5,
        }
        members.sort(key=lambda r: (order.get(r["status"], 9), r["name"]))
        return {
            **self.brief(org, day),
            "list_note": org.get("list_note") or "",
            "sources": org.get("sources") or [],
            "members": members,
            "alive": _alive(org, day),
        }

    def for_state(self, ctx, qids: set[str], day: str) -> list[dict]:
        out = []
        for org in self.orgs:
            if not _alive(org, day):
                continue
            hit = None
            for m in org.get("members") or []:
                keys = set(m.get("match") or [])
                if m.get("qid"):
                    keys.add(m["qid"])
                if keys & qids:
                    hit = self._row(ctx, org, m, day)
                    break
            if hit and hit["status"]:
                out.append({**self.brief(org, day), "qualification": hit["status"], "member": hit})
            elif org.get("incomplete"):
                out.append({
                    **self.brief(org, day),
                    "qualification": "名单没有写到这个政权",
                    "member": None,
                })
        return out


def load_diplomacy(data_dir) -> Diplomacy:
    raw = json.loads((data_dir / "curated" / "diplomacy.json").read_text(encoding="utf-8"))
    return Diplomacy(raw.get("orgs") or [])


class DiplomacyModule(ContentModule):
    id = "diplomacy"
    title = "外交 / 国际组织"
    order = 11
    description = "所选日期该政权在这一批已核对组织里的资格。没有写到，不等于不是会员。"
    frontend = "modules/diplomacy.js"
    source = "各组织条目下列出来源。名单不完整的不编造其余会员。"

    def load(self, ctx):
        self.ctx = ctx
        self.data = load_diplomacy(ctx.data_dir)

    def stats(self):
        return {"orgs": len(self.data.orgs)}

    def _qids(self, ctx, polity, date, params) -> set[str]:
        st, _alts = pick_state(ctx, polity, date, params)
        if not st:
            return set()
        qids = {st["id"]}
        for extra in params.get("_strong") or []:
            if extra.get("id"):
                qids.add(extra["id"])
        return qids

    def query(self, ctx, polity, date, params):
        day, grain = view_day(date)
        alive = self.data.alive(day)
        note = grain
        if polity is None:
            return {
                "items": alive, "total": len(alive), "shown": True, "kind": "list",
                "note": note or "没有点选国家。下面是这一天还在的组织。",
                "date_note": grain, "day": day,
            }
        qids = self._qids(ctx, polity, date, params)
        if not qids:
            return {
                "items": alive, "total": len(alive), "shown": True, "kind": "list",
                "note": (note + " " if note else "") + "没有把这个区域对应到当时的政权。下面仍是这一天还在的组织。",
                "date_note": grain, "day": day,
            }
        rows = self.data.for_state(ctx, qids, day)
        return {
            "items": rows, "total": len(rows), "shown": True, "kind": "state",
            "note": note, "date_note": grain, "day": day,
            "coverage": "只显示这一批写了资格的组织。标了名单不完整的，没有写到这个政权，就不判断它是不是会员。",
        }


MODULE = DiplomacyModule()
