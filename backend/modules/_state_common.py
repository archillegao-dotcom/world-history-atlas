"""政权类模块共用：取得点击的多边形在所选日期对应的 Wikidata 政权（可由用户切换）。"""
from __future__ import annotations

from ..polity import PolityResolver


def resolver(ctx) -> PolityResolver:
    if "polity" not in ctx.shared:
        ctx.shared["polity"] = PolityResolver(ctx.data_dir)
    return ctx.shared["polity"]


def pick_state(ctx, polity, date, params):
    """返回 (主要政权 dict 或 None, 候选列表[{id,name,method}])。params["state"] 可指定 QID。
    另外把「同名强候选」列表放在 params["_strong"]，供领导人/政权性质模块合并数据用。"""
    if polity is None:
        return None, []
    R = resolver(ctx)
    cands = R.resolve(params.get("snap"), polity["props"]["fid"], date)
    alts = [{"id": c["state"]["id"], "name": c["state"].get("zh") or c["state"].get("en"),
             "en": c["state"].get("en"), "method": c["method"]} for c in cands]
    params["_strong"] = [c["state"] for c in cands if c["strong"]]
    want = params.get("state")
    if want and want in R.states:
        params["_strong"] = [R.states[want]]   # 用户手动指定时只用该政权
        return R.states[want], alts
    return (cands[0]["state"] if cands else None), alts


METHOD_ZH = {"naturalearth": "Natural Earth 自带 ID", "wiki-title": "同名维基条目", "name": "名称匹配",
             "capital": "首都位于此范围", "coord": "坐标位于此范围",
             "capital+name": "首都位于此范围且名称相近", "coord+name": "坐标位于此范围且名称相近"}
