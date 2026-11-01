"""政权类模块共用：取得点击的多边形在所选日期对应的 Wikidata 政权（可由用户切换）。"""
from __future__ import annotations

from ..polity import PolityResolver


def resolver(ctx) -> PolityResolver:
    if "polity" not in ctx.shared:
        ctx.shared["polity"] = PolityResolver(ctx.data_dir)
        ctx.shared["polity"].geo = ctx.basemaps
    return ctx.shared["polity"]


def pick_state(ctx, polity, date, params):
    """返回 (主要政权 dict 或 None, 候选列表[{id,name,method}])。params["state"] 可指定 QID。
    另外把「同名强候选」列表放在 params["_strong"]，供领导人/政权性质模块合并数据用。"""
    if polity is None:
        return None, []
    R = resolver(ctx)
    cands = R.resolve(params.get("snap"), polity["props"]["fid"], date)
    alts = [{"id": c["state"]["id"], "name": c["state"].get("zh") or c["state"].get("en"),
             "en": c["state"].get("en"), "method": c["method"], "strong": c["strong"]} for c in cands]
    # 合并显示的「同名强候选」：只合并与主要政权**中文名相同**的强候选（如 1912–1949 与 1912 至今两个
    # 「中华民国」条目）。名称不同的政权（中华人民共和国 / 中华民国、东德 / 德国、朝鲜 / 韩国）绝不合并，
    # 否则会把另一个政权的领导人、条约、政体显示到这个政权的面板里。
    # 近代以后：没有强候选时，允许「首都位于此范围」的唯一政权作为主要政权（如 1946 年的英属巴勒斯坦托管地），
    # 面板会显示匹配方式；1800 年以前不这样做（首都匹配在古代常把后世的地方政权套到早期多边形上）；
    # 多个政权的首都都在范围内（旧多边形已分裂）时不选（见 PolityResolver.primary）
    _p = R.primary(cands, date)
    prim = _p["state"] if _p else None
    params["_split"] = R.split_names(cands) if prim is None else []
    pz = prim and (prim.get("zh") or prim.get("en"))
    pm = next((c["method"] for c in cands if c["state"] is prim), None)
    dk = date.key()
    pcap = prim and R.capital_at(prim, dk)

    def same_entity(c):
        """同一个国家在 Wikidata 中的不同粒度条目才合并：中文名相同；或者（都不是朝代时间轴候选）当时的首都相同
        （相距 < 1°，如 1500 年「法兰西王国」与「法国」都在巴黎）。首都不同的政权（中华人民共和国 / 中华民国、
        满洲国 / 中华民国、朝鲜 / 韩国）绝不合并，否则会把另一个政权的领导人、政体显示到这个政权的面板里。"""
        st = c["state"]
        if st is prim:
            return True
        if pz and (st.get("zh") or st.get("en")) == pz:
            return True
        if c["method"] in ("dynasty", "territory") or pm in ("dynasty", "territory"):
            return False
        if not pcap:
            # 主要条目没有首都记录（如「奥斯曼帝国哈里发」）：与首都位于本多边形内的强候选合并（如「奥斯曼帝国」）
            return not prim.get("capitals") and R._seat_fid(params.get("snap"), st, dk) == polity["props"]["fid"]
        cc = R.capital_at(st, dk)
        return bool(cc) and abs(cc[0] - pcap[0]) < 1.0 and abs(cc[1] - pcap[1]) < 1.0
    params["_strong"] = [c["state"] for c in cands if c["strong"] and same_entity(c)]
    want = params.get("state")
    if want and want in R.states:
        params["_strong"] = [R.states[want]]   # 用户手动指定时只用该政权
        return R.states[want], alts
    # 主要政权只从「强」候选中选；只有首都/坐标落在范围内的弱候选只作为参考列出，不当作这个区域的政权
    return (prim if prim else None), alts


METHOD_ZH = {"naturalearth": "Natural Earth 自带 ID", "wiki-title": "同名维基条目", "name": "名称匹配",
             "capital": "首都位于此范围", "coord": "坐标位于此范围",
             "capital+name": "首都位于此范围且名称相近", "coord+name": "坐标位于此范围且名称相近",
             "predecessor": "前身政权（Wikidata P1365，该地区的现代政权当时尚未成立）",
             "successor": "继承政权（Wikidata P1366，首都位于此范围）",
             "dynasty": "中国朝代时间轴（data/curated/china_dynasties.json，日期取自 Wikidata）",
             "territory": "特殊地位领土（Natural Earth 1:10m 范围；Wikidata 该领土及其前身条目）"}


def split_note(params):
    """旧政权已分裂（见 PolityResolver.split_names）时面板的说明。"""
    sp = params.get("_split") or []
    if not sp:
        return None
    return (f"这一地图区域在所选日期已分裂为 {'、'.join(sp[:6])} 等政权；底图边界要到下一张快照才更新，"
            "因此不把整个旧范围归给其中任何一个。可在下面的候选中选择查看。")
