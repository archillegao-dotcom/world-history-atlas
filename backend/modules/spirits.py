"""
面板模块「国家精神」：所选日期该政权作为签署方/参与方、正在生效的条约与同盟，以卡片显示。

条约数据：data/treaties.json.gz（tools/build_treaties.py；Wikidata treaty Q131569 及子类）。
- 开始：生效日期 P7588，否则签订日期 P585，否则开始时间 P580 / 成立 P571；没有任何日期的条约不显示（无法定位到时间上）。
- 结束：P582 / P576。有结束日期的按日期判断；**没有记录结束时间的**单独归为「已签订、未记录终止」，
  只要签署的那个政权当时仍然存在就列出（Wikidata 极少记录条约失效，不能据此断定仍然有效）。
- 匹配：该区域当时存在的「强」候选政权（名称匹配等，见 backend/polity.py），任一是签署方即可；
  卡片上注明是通过哪个政权匹配的。只凭首都位置匹配的弱候选（多为下级行政区）不参与，以免噪声。
同盟卡片来自「阵营地图」的数据（同一套成员与时间规则）。
"""
from __future__ import annotations

from ..zh import disp as _zh_disp

import collections
import json
from pathlib import Path

from ..polity import alive
from ..registry import ContentModule
from ..timeutil import rec_key
from ._common import fmt_time, load_records
from ._state_common import METHOD_ZH, pick_state, resolver


def tstart(r):
    return r.get("effective") or r.get("signed") or r.get("start") or r.get("inception")


def tend(r):
    return r.get("end") or r.get("dissolved")


_FIX_FIELDS = ("zh", "en", "desc", "parties", "countries", "signed", "adopted", "effective",
                "intended_effective", "end", "types", "status", "also_show", "enwiki", "zhwiki", "sl")


def apply_treaty_fixes(recs, data_dir, fixes=None):
    """人工改掉有证据的错译、错归属。只改列出的条目，不重跑机器翻译。

    insert=true 的条目是公开文献里有、但这份 Wikidata 导出里没有的文件。不发明 QID。
    hide=true 的条目不再进入面板。fixes 给定时不读文件，供审计比较修正前后。
    """
    if fixes is None:
        p = Path(data_dir) / "curated" / "treaty_fixes.json"
        if not p.exists():
            return
        fixes = json.loads(p.read_text(encoding="utf-8"))
    by = {r.get("id"): r for r in recs if isinstance(r, dict)}
    dropped = set()
    for tid, fx in fixes.items():
        if tid.startswith("_") or not isinstance(fx, dict):
            continue
        if fx.get("hide"):
            dropped.add(tid)
            continue
        r = by.get(tid)
        if not r:
            if not fx.get("insert"):
                continue
            r = {"id": tid, "sl": fx.get("sl", 20), "zh_mt": False, "parties": [], "types": []}
            recs.append(r)
            by[tid] = r
        for k in _FIX_FIELDS:
            if k in fx:
                r[k] = fx[k]
        r["zh_mt"] = False
        if fx.get("summary_zh"):
            r["summary"] = {"text": fx["summary_zh"], "src": "curated", "mt": False,
                            "url": (fx.get("sources") or [None])[0]}
            r.pop("zhwiki", None)
            r.pop("enwiki", None)
        elif fx.get("drop_mt_summary") and isinstance(r.get("summary"), dict):
            sm = r["summary"]
            sm.pop("text", None)
            sm["mt"] = False
        if fx.get("note"):
            r["fix_note"] = fx["note"]
        r["fix_sources"] = fx.get("sources", [])
    if dropped:
        recs[:] = [r for r in recs if r.get("id") not in dropped]


STATUS_ZH = {
    "signed_then_effective": "先签署，到记载的生效日才生效",
    "signed_not_yet_effective": "已签署未生效",
    "signed_never_effective": "已签署未生效",
    "signed_not_ratified": "已签署，未获批准，不作为生效条约",
    "published_not_ratified": "签署当日公布并付诸实施，没有议会批准",
}


def view_of(r, date_str):
    """按所选日期决定弹窗里哪些日期和正文可以出现。

    这一版自己的生效日在生效前仍然显示，并标成已签署未生效。
    还没到的终止日、以及尚未签署的整版正文，不放进当日视图。
    """
    if not date_str:
        return {}
    from ..timeutil import parse_date
    dk = parse_date(date_str).key()
    signed = r.get("signed") or r.get("adopted")
    sk, ek = rec_key(signed), rec_key(r.get("effective"))
    end = tend(r)
    endk = rec_key(end)
    if sk is not None and dk < sk:
        return {"withhold": True, "view_status": "所选日期这一版尚未签署"}
    out = {}
    if r.get("status") == "signed_never_effective" or (ek is not None and dk < ek):
        out["view_status"] = "已签署未生效"
    elif endk is not None and dk > endk:
        out["view_status"] = "已终止或在缔约方之间被取代"
    if endk is not None and dk < endk:
        out["hide_end"] = True
    return out


def kind_of(r) -> str:
    en = " ".join((t.get("en") or "") + " " + (t.get("zh") or "") for t in r.get("types", [])).lower()
    if "alliance" in en or "defen" in en:
        return "同盟"
    if "protocol" in en or "议定书" in en:
        return "议定书"
    if "armistice" in en or "停战" in en:
        return "停战协定"
    if "peace" in en or "capitulation" in en:
        return "和约"
    if any(w in en for w in ("trade", "investment", "economic", "customs", "commerce", "tax")):
        return "经贸"
    if any(w in en for w in ("border", "boundary", "cession", "territor")):
        return "领土"
    return "条约"


class SpiritsModule(ContentModule):
    id = "spirits"
    title = "国家精神"
    order = 10
    description = "当时正在生效的条约与同盟（Wikidata 条约及签署方）"
    frontend = "modules/statepanels.js"
    source = "Wikidata（treaty Q131569 及子类；签署方 P1891、参与方 P710、签订 P585、生效 P7588、终止 P582/P576，CC0）"

    def load(self, ctx):
        self.recs = load_records(Path(ctx.data_dir) / "treaties.json.gz")
        from ..zh import fill as zh_fill
        zh_fill(self.recs, ctx.data_dir)
        apply_treaty_fixes(self.recs, ctx.data_dir)
        self.by_id = {r["id"]: r for r in self.recs}
        self.by_party = collections.defaultdict(list)
        for r in self.recs:
            seen_party = set()
            for p in r.get("parties", []) + r.get("also_show", []):
                if p.get("s") and p["s"] not in seen_party:
                    seen_party.add(p["s"])
                    self.by_party[p["s"]].append(r)
        ctx.shared["treaties"] = self.by_id

    def stats(self):
        return {"treaties": len(self.recs), "with_parties": sum(1 for r in self.recs if r.get("parties"))}

    def query(self, ctx, polity, date, params):
        if polity is None:
            return {"items": [], "total": 0, "note": "请点击一个国家/政权。"}
        R = resolver(ctx)
        st, alts = pick_state(ctx, polity, date, params)
        cands = R.resolve(params.get("snap"), polity["props"]["fid"], date)
        group = {}
        if params.get("state"):
            group[params["state"]] = "所选政权"
        else:
            for c in cands:
                if c["strong"]:
                    group.setdefault(c["state"]["id"], METHOD_ZH.get(c["method"], c["method"]))
        dk = date.key()
        buckets = {"dated": [], "open": [], "pending": [], "never": [], "unratified": [], "implemented": []}
        seen = set()
        for sid, how in group.items():
            for r in self.by_party.get(sid, []):
                if r["id"] in seen or not (r.get("zh") or r.get("en")):
                    continue
                signed = r.get("signed")
                eff = r.get("effective")
                end = tend(r)
                start = signed or tstart(r)
                a, b = rec_key(start), rec_key(end)
                if a is None or a > dk or (b is not None and dk > b + (0.999 if not end.get("m") else 0)):
                    continue
                party_ids = {p["s"] for p in r.get("parties", [])}
                also = {p["s"]: p.get("how") or "沿用，不是签署方" for p in r.get("also_show", [])}
                if sid not in party_ids and sid not in also:
                    continue
                seen.add(r["id"])
                status = r.get("status")
                if status == "signed_not_ratified":
                    which = "unratified"
                elif status == "published_not_ratified":
                    which = "implemented"
                elif status == "signed_never_effective":
                    which = "never"
                elif eff and signed and rec_key(eff) is not None and dk < rec_key(eff):
                    which = "pending"
                elif end is not None:
                    which = "dated"
                else:
                    which = "open"
                status_zh = STATUS_ZH.get(status)
                if which == "pending" and status == "signed_not_yet_effective":
                    status_zh = "已签署未生效"
                elif which == "never":
                    status_zh = "已签署未生效"
                elif which == "dated" and status == "signed_not_yet_effective":
                    status_zh = None
                card = {"id": r["id"], "name": __import__("backend.zh", fromlist=["disp"]).disp(r.get("zh") or r.get("en")), "en": r.get("en"), "kind": kind_of(r),
                        "types": [t.get("zh") or t.get("en") for t in r.get("types", [])][:3],
                        "from": fmt_time(start), "to": fmt_time(end) if end and rec_key(end) is not None and dk >= rec_key(end) else None,
                        "parties": [R.state_name(p["s"]) for p in r.get("parties", [])][:12],
                        "n_parties": len(r.get("parties", [])), "via": R.state_name(sid), "via_how": how,
                        "role": None if sid in party_ids else also.get(sid),
                        "status": status, "status_zh": status_zh,
                        "sl": r.get("sl") or 0, "_k": a}
                buckets[which].append(card)
        dated, open_ = buckets["dated"], buckets["open"]
        dated.sort(key=lambda c: -c["_k"])
        open_.sort(key=lambda c: (-c["sl"] if dk - c["_k"] > 50 else -1e6 - c["_k"]))  # 近 50 年内的按时间，其余按知名度
        for key in ("pending", "never", "unratified", "implemented"):
            buckets[key].sort(key=lambda c: -c["_k"])
        blocs = []
        act = ctx.shared.get("alliances_active")
        if act:
            for a in act(ctx, date):
                if set(group) & set(a["members"]):
                    blocs.append({"id": a["id"], "name": a["name"], "n": len(a["members"]), "no_end": a.get("no_end")})
        for c in dated + open_ + buckets["pending"] + buckets["never"] + buckets["unratified"] + buckets["implemented"]:
            c.pop("_k", None)
        n = (len(dated) + len(open_) + len(blocs) + len(buckets["pending"]) + len(buckets["never"])
             + len(buckets["unratified"]) + len(buckets["implemented"]))
        return {"items": [], "total": n, "kind": "spirits", "blocs": blocs, "dated": dated[:60], "open": open_[:60],
                "pending": buckets["pending"][:20], "never": buckets["never"][:20],
                "unratified": buckets["unratified"][:20], "implemented": buckets["implemented"][:20],
                "n_dated": len(dated), "n_open": len(open_), "matched": [{"id": k, "name": R.state_name(k), "how": v} for k, v in group.items()],
                "state": st and {"id": st["id"], "name": _zh_disp(st.get("zh") or st.get("en"))},
                "alternatives": [{**a, "method_zh": METHOD_ZH.get(a["method"], a["method"])} for a in alts],
                "note": "「未记录终止」只表示没有终止日期，不代表仍然有效。「已签署未生效」是已经签署、生效日还没到，或记载中没有生效。「未批准」不作为生效条约。本批核对了四份法国相关文件。斯洛伐克共和国、克罗地亚独立国、汪精卫政权、满洲国、意大利社会共和国的条约缺口没有逐份编目。"}


MODULE = SpiritsModule()
