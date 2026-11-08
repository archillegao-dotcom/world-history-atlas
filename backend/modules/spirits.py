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


def apply_treaty_fixes(recs, data_dir):
    """人工改掉有证据的错译、错归属。只改列出的条目，不重跑机器翻译。"""
    p = Path(data_dir) / "curated" / "treaty_fixes.json"
    if not p.exists():
        return
    fixes = json.loads(p.read_text(encoding="utf-8"))
    by = {r.get("id"): r for r in recs if isinstance(r, dict)}
    for tid, fx in fixes.items():
        if tid.startswith("_"):
            continue
        r = by.get(tid)
        if not r:
            continue
        for k in ("zh", "desc", "parties", "countries"):
            if k in fx:
                r[k] = fx[k]
        r["zh_mt"] = False
        if fx.get("drop_mt_summary") and isinstance(r.get("summary"), dict):
            sm = r["summary"]
            sm.pop("text", None)
            sm["mt"] = False
        if fx.get("note"):
            r["fix_note"] = fx["note"]
        r["fix_sources"] = fx.get("sources", [])


def kind_of(r) -> str:
    en = " ".join((t.get("en") or "") for t in r.get("types", [])).lower()
    if "alliance" in en or "defen" in en:
        return "同盟"
    if "peace" in en or "armistice" in en or "capitulation" in en:
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
            for p in r.get("parties", []):
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
        dated, open_ = [], []
        seen = set()
        for sid, how in group.items():
            for r in self.by_party.get(sid, []):
                if r["id"] in seen or not (r.get("zh") or r.get("en")):
                    continue
                a, b = rec_key(tstart(r)), rec_key(tend(r))
                if a is None or a > dk or (b is not None and dk > b + (0.999 if not tend(r).get("m") else 0)):
                    continue
                seen.add(r["id"])
                card = {"id": r["id"], "name": __import__("backend.zh", fromlist=["disp"]).disp(r.get("zh") or r.get("en")), "en": r.get("en"), "kind": kind_of(r),
                        "types": [t.get("zh") or t.get("en") for t in r.get("types", [])][:3],
                        "from": fmt_time(tstart(r)), "to": fmt_time(tend(r)) if tend(r) else None,
                        "parties": [R.state_name(p["s"]) for p in r.get("parties", [])][:12],
                        "n_parties": len(r.get("parties", [])), "via": R.state_name(sid), "via_how": how,
                        "sl": r["sl"], "_k": a}
                (dated if b is not None else open_).append(card)
        dated.sort(key=lambda c: -c["_k"])
        open_.sort(key=lambda c: (-c["sl"] if dk - c["_k"] > 50 else -1e6 - c["_k"]))  # 近 50 年内的按时间，其余按知名度
        blocs = []
        act = ctx.shared.get("alliances_active")
        if act:
            for a in act(ctx, date):
                if set(group) & set(a["members"]):
                    blocs.append({"id": a["id"], "name": a["name"], "n": len(a["members"]), "no_end": a.get("no_end")})
        for c in dated + open_:
            c.pop("_k", None)
        n = len(dated) + len(open_) + len(blocs)
        return {"items": [], "total": n, "kind": "spirits", "blocs": blocs, "dated": dated[:60], "open": open_[:60],
                "n_dated": len(dated), "n_open": len(open_), "matched": [{"id": k, "name": R.state_name(k), "how": v} for k, v in group.items()],
                "state": st and {"id": st["id"], "name": _zh_disp(st.get("zh") or st.get("en"))},
                "alternatives": [{**a, "method_zh": METHOD_ZH.get(a["method"], a["method"])} for a in alts],
                "note": "「未记录终止」表示 Wikidata 没有记录这份条约的终止/失效时间（不代表一定仍然有效）。"}


MODULE = SpiritsModule()
