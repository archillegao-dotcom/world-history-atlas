"""政权类模块共用：取得点击的多边形在所选日期对应的 Wikidata 政权（可由用户切换）。"""
from __future__ import annotations

from ..zh import disp as _zh_disp

from ..polity import PolityResolver
from ..timeutil import rec_key


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
    alts = [{"id": c["state"]["id"], "name": _zh_disp(c["state"].get("zh") or c["state"].get("en")),
             "en": c["state"].get("en"), "method": c["method"], "strong": c["strong"]} for c in cands]
    # 合并显示的「同名强候选」：只合并与主要政权**中文名相同**的强候选（如 1912–1949 与 1912 至今两个
    # 「中华民国」条目）。名称不同的政权（中华人民共和国 / 中华民国、东德 / 德国、朝鲜 / 韩国）绝不合并，
    # 否则会把另一个政权的领导人、条约、政体显示到这个政权的面板里。
    # 近代以后：没有强候选时，允许「首都位于此范围」的唯一政权作为主要政权（如 1946 年的英属巴勒斯坦托管地），
    # 面板会显示匹配方式；1800 年以前不这样做（首都匹配在古代常把后世的地方政权套到早期多边形上）；
    # 多个政权的首都都在范围内（旧多边形已分裂）时不选（见 PolityResolver.primary）
    _p = R.primary(cands, date)
    if _p is not None and not params.get("state"):
        _p = _prefer_ruled(ctx, R, cands, _p, date, params)
    prim = _p["state"] if _p else None
    params["_split"] = R.split_names(cands) if prim is None else []
    params.pop("_dynasty_before_start", None)
    if prim and _p and _p.get("method") == "dynasty" and prim.get("from") and date.key() < rec_key(prim["from"]):
        params["_dynasty_before_start"] = (polity.get("props") or {}).get("NAME")
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
    # 政权更替链（如法兰西第四共和国 → 第五共和国）：当前行不是并立政权时，把该国的总条目（如「法国」）并入同组，
    # 这样领导人等按日期限定的数据仍可用（总条目的元首/首脑语句带起止日期，按日期过滤，不会串到别的时期）
    if prim is not None:
        from ..regimes import chain_for
        chn = chain_for(ctx.data_dir, [prim["id"]] + [x["id"] for x in params["_strong"]], dk)
        params["_chain"] = chn
        if chn and chn["merge_country"] and chn["country"] in R.states and chn["now"] and not any(r["parallel"] for r in chn["now"] if r.get("qid") == prim["id"]):
            if all(x["id"] != chn["country"] for x in params["_strong"]):
                params["_strong"].append(R.states[chn["country"]])
    want = params.get("state")
    if want and want in R.states:
        params["_strong"] = [R.states[want]]   # 用户手动指定时只用该政权
        return R.states[want], alts
    # 主要政权只从「强」候选中选；只有首都/坐标落在范围内的弱候选只作为参考列出，不当作这个区域的政权
    return (prim if prim else None), alts



# v0.6.1：几个候选政权都对应同一个多边形时的默认选择规则（通用规则，不针对个别政权）。
# 底图名称匹配到的条目常是泛称或长时段条目（如 430 年的「波斯」、842 年的「加洛林帝国」），这一天在
# Wikidata / 整理数据里没有任何在位者；而首都在此范围内的另一个候选（萨珊王朝、法兰克王国）这一天有
# 在位君主或空位期/共治案例。规则：默认政权（连同合并的同名条目）这一天既没有在位者也没有空位期案例时，
# 改选「这一天有空位期案例或在位者」的候选；有案例的优先，其次取存续期最短（最具体）的；
# 只有在位者（没有案例）的候选，只在默认条目是泛称/长时段条目（存续 ≥ 1000 年）时考虑，且候选存续期必须嵌套
# 在其中、长度不超过三分之一，避免把多边形里另一个并立政权（如 850 年加洛林多边形里的威尼斯）选为默认。整理过的对应（CShapes、殖民地宗主、二战、实际控制区、
# 整理名称表）不改。用户在下拉框里手动选择时不适用。
_TRUSTED = {"cshapes", "owner", "territory", "ww2", "naturalearth", "curated-name", "dynasty"}


def ruler_status(ctx, R, st, dk):
    """(有空位期/共治案例, 有在位者)：与领导人面板同一套判定（国家元首 / 带时间的职位 / interregna.json）。"""
    from .leaders import _holding, is_envoy
    from ..interregna import cases_at
    case = bool(cases_at(ctx.data_dir, [st["id"]], dk))
    if any(_holding([{"from": x.get("from"), "to": x.get("to"), "p": x["v"]} for x in st.get("hos", [])], dk)):
        return case, True
    for o in R.office_by_state.get(st["id"], []):
        if not is_envoy(o) and _holding(o.get("holders", []), dk):
            return case, True
    return case, False


def _prefer_ruled(ctx, R, cands, p, date, params):
    if p["method"] in _TRUSTED or p.get("zone"):
        return p
    dk = date.key()
    pz = p["state"].get("zh") or p["state"].get("en")
    group = [c["state"] for c in cands if c["state"] is p["state"] or (c["strong"] and (c["state"].get("zh") or c["state"].get("en")) == pz)]
    if any(any(ruler_status(ctx, R, s, dk)) for s in group):
        return p
    from ..polity import lifespan
    from ..timeutil import rec_key
    pa, pb, _ = lifespan(p["state"])
    pa, pb = (rec_key(pa) if pa else -1e9), (rec_key(pb) if pb else 2026.0)   # 至今存在的条目按到今年计
    seen, scored = set(), []
    for c in cands:
        st = c["state"]
        if st["id"] in seen or c is p:
            continue
        seen.add(st["id"])
        case, ruler = ruler_status(ctx, R, st, dk)
        if not (case or ruler):
            continue
        a, b, _ = lifespan(st)
        ka, kb = (rec_key(a) if a else -1e9), (rec_key(b) if b else 2026.0)
        scored.append((not case, kb - ka, c, ka, kb))
    if not scored:
        return p
    # 只有在位者（没有案例）的候选：存续期必须嵌套在默认条目的存续期之内（更具体的同地区政权，如「波斯」-550–1979
    # 之内的萨珊 224–651）；不嵌套的（如 850 年加洛林多边形里的威尼斯 697–1797）不选
    # 并且默认条目必须是「泛称 / 长时段」条目（存续期 ≥ 1000 年），候选的存续期不超过它的三分之一；
    # 两个时段相近的并立政权（高句丽 / 百济、米兰 / 蒙费拉托）之间不切换——那通常是首都坐标或底图粗糙造成的
    plen = pb - pa
    # 还要求它是其余候选中 Wikidata 站点链接最多（最知名）的一个——如 1783 年「波斯」多边形里赞德王朝这一天
    # 没有在位者记录时，不改选只是首都落在其中的塔雷什汗国
    top = max((c for c in cands if c["state"] is not p["state"]), key=lambda c: c["state"].get("sl") or 0)
    ok = [x for x in scored if not x[0] or (plen >= 1000 and pa <= x[3] and x[4] <= pb and x[1] * 3 <= plen
                                            and x[2]["state"]["id"] == top["state"]["id"])]
    if not ok:
        return p
    best = min(ok, key=lambda x: (x[0], x[1]))[2]
    params["_auto"] = {"from": p["state"]["id"], "from_name": _zh_disp(pz), "to": best["state"]["id"]}
    return best

METHOD_ZH = {"curated-name": "整理的底图名称对应（data/curated/name_candidates.json）", "ww2": "二战按日期数据（Stanford 按月边界 / 战线节点，人工核对的政权对应）", "cshapes": "CShapes 2.0 国家编码 + 人工核对的分期（带起止日期）", "owner": "宗主国（CShapes 记录的殖民地/保护国/托管地宗主）", "naturalearth": "Natural Earth 自带 ID", "wiki-title": "同名维基条目", "name": "名称匹配",
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
