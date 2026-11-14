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
    "merged": "已并入另一会员",
    "dissolved": "国家已停止存在，会籍不自动传给后继",
    "removed": "已从名册除去",
}

# 仍算在这一天的名册里。宣布退出但通知期未满的，盟约下还是会员。
_ON_ROLL = {
    "成员国", "会商国", "中国席位",
    "已宣布退出，通知期未满",
    "不自动延续原会籍，不得参加大会工作",
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
    jf, ju = m.get("join_uncertain_from"), m.get("join_uncertain_until")
    if jf and ju and jf <= day <= ju:
        return "加入日待考"
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
    special = m.get("special_from")
    if special and day >= special:
        return m.get("special_status") or "资格另有说明"
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
    def __init__(self, orgs: list[dict], organs: dict | None = None, acts: dict | None = None, ga_note: str = ""):
        self.orgs = orgs
        self.by_id = {o["id"]: o for o in orgs}
        self.organs = organs or {}
        self.acts = acts or {}
        self.ga_note = ga_note

    def _name(self, ctx, m: dict, day: str) -> str:
        R = resolver(ctx)
        for row in m.get("names") or []:
            if _on(day, row.get("from"), row.get("until")):
                if row.get("name"):
                    return row["name"]
                if row.get("qid"):
                    return R.state_name(row["qid"])
        if m.get("name"):
            return m["name"]
        chosen = m.get("qid")
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
            "不自动延续原会籍，不得参加大会工作": 2,
            "通知期满的日子各说来源不一致": 3,
            "加入日待考": 3,
            "签署方，后来的会籍未核": 4,
            "按年名单尚未加入": 5, "尚未加入": 5, "加入日未核": 5,
            "已退出": 6, "被开除": 6, "已并入另一会员": 6,
            "不再持有这一席位": 6, "席位待考": 6,
            "国家已停止存在，会籍不自动传给后继": 6,
            "已从名册除去": 6,
        }
        members.sort(key=lambda r: (order.get(r["status"], 9), r["name"]))
        active = [r for r in members if r["status"] in _ON_ROLL]
        return {
            **self.brief(org, day),
            "list_note": org.get("list_note") or "",
            "sources": org.get("sources") or [],
            "members": members,
            "active_count": len(active),
            "record_count": len(org.get("members") or []),
            "organs": self._organs(org["id"], day),
            "alive": _alive(org, day),
        }

    def _act_public(self, row: dict) -> dict:
        return {
            "date": row.get("date") or "",
            "zh": row.get("zh") or "",
            "url": row.get("url") or "",
            "label": row.get("label") or "",
            "kind": row.get("kind") or "",
        }

    def _organs(self, oid: str, day: str) -> list[dict]:
        out = []
        for node in self.organs.get(oid) or []:
            if not _on(day, node.get("from"), node.get("until")):
                continue
            rows = self.acts.get(node.get("id"))
            if rows is None:
                rows = node.get("acts") or []
            today = [self._act_public(a) for a in rows if a.get("date") == day]
            previous = None
            if not today:
                earlier = [a for a in rows if a.get("date") and a["date"] < day]
                if earlier:
                    last = max(a["date"] for a in earlier)
                    previous = {
                        "date": last,
                        "acts": [self._act_public(a) for a in earlier if a["date"] == last],
                    }
            out.append({
                "id": node.get("id"), "zh": node.get("zh"), "en": node.get("en") or "",
                "kind": node.get("kind"), "kind_zh": node.get("kind_zh") or "",
                "from": node.get("from"), "until": node.get("until"),
                "summary": node.get("summary") or "",
                "sources": node.get("sources") or [],
                "same_as": node.get("same_as") or "",
                "same_as_zh": node.get("same_as_zh") or "",
                "acts": today,
                "previous": previous,
                "acts_label": "当日无记录" if not today else "",
                "acts_note": self.ga_note if node.get("id") == "ga" else "",
            })
        return out

    def for_state(self, ctx, qids: set[str], day: str) -> list[dict]:
        out = []
        for org in self.orgs:
            if not _alive(org, day):
                continue
            hits = []
            names = set()
            R = resolver(ctx)
            for q in qids:
                label = R.state_name(q)
                if label:
                    names.add(label)
            for m in org.get("members") or []:
                keys = set(m.get("match") or [])
                if m.get("qid"):
                    keys.add(m["qid"])
                row = self._row(ctx, org, m, day)
                if not row["status"]:
                    continue
                if keys & qids or (row["name"] and row["name"] in names):
                    hits.append(row)
            hit = _prefer(hits)
            if hit and hit["status"]:
                out.append({**self.brief(org, day), "qualification": hit["status"], "member": hit})
            elif org.get("incomplete"):
                out.append({
                    **self.brief(org, day),
                    "qualification": "名单没有写到这个政权",
                    "member": None,
                })
        return out


def _prefer(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    rank = {
        "成员国": 0, "会商国": 0, "中国席位": 0,
        "已宣布退出，通知期未满": 1,
        "不自动延续原会籍，不得参加大会工作": 2,
        "加入日待考": 3,
        "已退出": 4, "被开除": 4, "已并入另一会员": 4,
        "不再持有这一席位": 4, "已从名册除去": 4,
        "国家已停止存在，会籍不自动传给后继": 4,
        "尚未加入": 5,
    }
    rows.sort(key=lambda r: (rank.get(r["status"], 9), r.get("from") or ""))
    return rows[0]


def load_diplomacy(data_dir) -> Diplomacy:
    base = data_dir / "curated"
    raw = json.loads((base / "diplomacy.json").read_text(encoding="utf-8"))
    for org in raw.get("orgs") or []:
        fn = org.get("members_file")
        if fn:
            org["members"] = json.loads((base / fn).read_text(encoding="utf-8")).get("members") or []
    organs = {}
    path = base / "diplomacy_organs.json"
    if path.exists():
        organs = json.loads(path.read_text(encoding="utf-8"))
    acts = {}
    ga_note = ""
    act_path = base / "diplomacy_acts.json"
    if act_path.exists():
        blob = json.loads(act_path.read_text(encoding="utf-8"))
        ga_note = blob.get("ga_note") or ""
        for key, rows in (blob.get("organs") or {}).items():
            acts[key] = sorted(rows, key=lambda a: (a.get("date") or "", a.get("zh") or ""))
    return Diplomacy(raw.get("orgs") or [], organs, acts, ga_note)


class DiplomacyModule(ContentModule):
    id = "diplomacy"
    title = "外交 / 国际组织"
    order = 11
    description = "所选日期该政权在已核对组织里的资格。名单写全的，对不上名字就不另判。"
    frontend = "modules/diplomacy.js"
    source = "联合国和国际联盟的名册写全。其余组织仍标名单不完整。"

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
