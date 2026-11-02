"""
详情接口：人物页面、职位/机构卡片、阵营面板、多边形对应的政权。
本地数据（data/states|offices|persons|orgs|alliances）+ 在线补充（维基百科摘要、Wikidata 担任职务），
在线内容缓存在用户数据目录；没有网络时只显示本地数据并注明。
"""
from __future__ import annotations

from .zh import disp as _zh_disp

import json

from fastapi import APIRouter, HTTPException

from .live import wiki
from .modules._common import fmt_time
from .modules._state_common import METHOD_ZH, resolver
from .polity import valid_at
from .timeutil import HDate, parse_date, rec_key

router = APIRouter()


def _ctx():
    from .app import ctx
    return ctx


def _t(t):
    return fmt_time(t) if t else None


def parse_json_time(dv: dict | None):
    """Wikidata JSON 时间（历史纪年，'-0551' = 公元前551年）-> {"y","m","d","p"}。"""
    if not dv or "time" not in dv:
        return None
    t = dv["time"]
    neg = t.startswith("-")
    body = t[1:]
    try:
        y, m, d = body[:body.index("T")].split("-")
        y, m, d = int(y), int(m), int(d)
    except ValueError:
        return None
    p = dv.get("precision", 9)
    return {"y": -y if neg else y, "m": m if p >= 10 else 0, "d": d if p >= 11 else 0, "p": p}


def _label(ent: dict) -> str | None:
    labs = ent.get("labels", {})
    for l in ("zh-cn", "zh-hans", "zh", "zh-hant", "en"):
        if l in labs:
            return labs[l]["value"]
    return None


def _t2s(s):
    try:
        from opencc import OpenCC
        return OpenCC("t2s").convert(s) if s else s
    except ImportError:
        return s


@router.get("/api/person/{pid}")
def person(pid: str):
    """人物页面。"""
    R = resolver(_ctx())
    p = R.persons.get(pid) or {}
    out = {"id": pid, "name": _zh_disp(p.get("zh") or p.get("en")), "en": p.get("en"), "desc": p.get("desc"),
           "born": _t(p.get("born")), "died": _t(p.get("died")),
           "party": [{"name": _zh_disp(x.get("zh") or x.get("en")), "from": _t(x.get("from")), "to": _t(x.get("to"))}
                     for x in p.get("party", [])],
           "img": wiki.commons_thumb(p.get("img")), "positions": [], "online": False, "summary": None,
           "links": [{"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{pid}"}]}
    zh_t, en_t = p.get("zhwiki"), p.get("enwiki")
    ent = wiki.entities([pid]).get(pid)
    if ent and "claims" in ent:
        out["online"] = True
        out["name"] = out["name"] or _t2s(_label(ent))
        if not out["desc"]:
            ds = ent.get("descriptions", {})
            out["desc"] = _t2s(next((ds[l]["value"] for l in ("zh-cn", "zh-hans", "zh", "en") if l in ds), None))
        sl = ent.get("sitelinks", {})
        zh_t = zh_t or sl.get("zhwiki", {}).get("title")
        en_t = en_t or sl.get("enwiki", {}).get("title")
        cl = ent["claims"]
        if not out["img"] and cl.get("P18"):
            out["img"] = wiki.commons_thumb(cl["P18"][0]["mainsnak"].get("datavalue", {}).get("value"))
        if not out["born"] and cl.get("P569"):
            out["born"] = _t(parse_json_time(cl["P569"][0]["mainsnak"].get("datavalue", {}).get("value")))
        if not out["died"] and cl.get("P570"):
            out["died"] = _t(parse_json_time(cl["P570"][0]["mainsnak"].get("datavalue", {}).get("value")))
        # 担任职务 P39（含起止）
        pos = []
        for c in cl.get("P39", []):
            pid2 = c["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
            q = c.get("qualifiers", {})
            f = parse_json_time(q.get("P580", [{}])[0].get("datavalue", {}).get("value")) if q.get("P580") else None
            t = parse_json_time(q.get("P582", [{}])[0].get("datavalue", {}).get("value")) if q.get("P582") else None
            if pid2:
                pos.append({"id": pid2, "from": f, "to": t})
        labs = wiki.entities(sorted({x["id"] for x in pos}), props="labels") if pos else {}
        pos.sort(key=lambda x: (x["from"] or {"y": 99999})["y"])
        out["positions"] = [{"id": x["id"], "name": _t2s(_label(labs.get(x["id"], {}))) or x["id"],
                             "from": _t(x["from"]), "to": _t(x["to"])} for x in pos]
    if zh_t:
        out["links"].append({"label": "中文维基", "url": f"https://zh.wikipedia.org/wiki/{zh_t.replace(' ', '_')}"})
    if en_t:
        out["links"].append({"label": "English Wikipedia", "url": f"https://en.wikipedia.org/wiki/{en_t.replace(' ', '_')}"})
    out["summary"] = wiki.summary(zh_t, en_t)
    if out["summary"] and not out["img"]:
        out["img"] = out["summary"].get("thumb")
    return out


@router.get("/api/office/{oid}")
def office(oid: str, date: str | None = None):
    """职位/机构卡片：职位与所领导机构的维基百科摘要（说明职能）、历任者（按时间）。"""
    R = resolver(_ctx())
    o = next((x for x in R.offices if x["id"] == oid), None)
    if not o:
        raise HTTPException(404, "没有这个职位")
    orgs = []
    for g in o.get("orgs", []):
        r = R.orgs.get(g, {})
        orgs.append({"id": g, "name": _zh_disp(r.get("zh") or r.get("en") or g), "desc": r.get("desc"),
                     "summary": wiki.summary(r.get("zhwiki"), r.get("enwiki"))})
    holders = sorted(o.get("holders", []), key=lambda h: (h.get("from") or {"y": 99999})["y"])
    return {"id": oid, "name": _zh_disp(o.get("zh") or o.get("en")), "en": o.get("en"), "desc": o.get("desc"),
            "juris": [{"id": s, "name": R.state_name(s)} for s in o.get("juris", [])],
            "summary": wiki.summary(o.get("zhwiki"), o.get("enwiki")), "orgs": orgs,
            "holders": [{"person": R.person_brief(h["p"]), "from": _t(h.get("from")), "to": _t(h.get("to"))} for h in holders],
            "links": [{"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{oid.split('@')[0]}"}]}


@router.get("/api/alliance/{aid}")
def alliance(aid: str, date: str | None = None):
    """阵营面板：成立/解散、成员（加入/退出）、领导/核心人物、维基百科摘要。"""
    ctx = _ctx()
    R = resolver(ctx)
    a = next((x for x in ctx.shared.get("alliances", []) if x["id"] == aid), None)
    if not a:
        raise HTTPException(404, "没有这个阵营")
    dk = parse_date(date).key() if date else None
    ROLE = {"P488": "主席", "P35": "元首", "P6": "首脑", "P1037": "负责人", "P112": "创始人", "P3342": "重要人物"}
    # 同一成员可能有多条记录（多段成员期，或不同 Wikidata 属性给出的不同日期）：合并为一行
    VIA = {"P527": "阵营条目「组成部分」", "P710": "阵营条目「参与者」", "P1891": "阵营条目「签署方」", "P463": "成员国条目「成员属于」"}
    by = {}
    for m in a["members"]:
        f, t = m.get("from"), m.get("to")
        e = by.setdefault(m["s"], {"id": m["s"], "name": R.state_name(m["s"]), "periods": [], "active": False, "_k": 1e9})
        via = m.get("via") or ""
        if via.startswith("treaty:"):
            tr = ctx.shared.get("treaties", {}).get(via[7:], {})
            via = f"条约「{tr.get('zh') or tr.get('en') or via[7:]}」的签署方/参与方"
        e["periods"].append({"from": _t(f), "to": _t(t), "via": VIA.get(via, via)})
        e["active"] |= dk is not None and valid_at(dk, f or a.get("from"), t or a.get("to"))
        k = rec_key(f)
        if k is not None:
            e["_k"] = min(e["_k"], k)
    members = sorted(by.values(), key=lambda x: (not x["active"], x.pop("_k")))
    leaders = [{"person": R.person_brief(x["p"]), "role": ROLE.get(x["role"], x["role"]),
                "from": _t(x.get("from")), "to": _t(x.get("to"))} for x in a.get("leaders", [])]
    links = [{"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{aid}"}]
    if a.get("zhwiki"):
        links.append({"label": "中文维基", "url": f"https://zh.wikipedia.org/wiki/{a['zhwiki'].replace(' ', '_')}"})
    if a.get("enwiki"):
        links.append({"label": "English Wikipedia", "url": f"https://en.wikipedia.org/wiki/{a['enwiki'].replace(' ', '_')}"})
    return {"id": aid, "name": _zh_disp(a.get("zh") or a.get("en")), "en": a.get("en"), "desc": a.get("desc"),
            "from": _t(a.get("from")), "to": _t(a.get("to")), "members": members, "leaders": leaders,
            "summary": wiki.summary(a.get("zhwiki"), a.get("enwiki")), "links": links,
            "treaties": [{"id": t, "name": (ctx.shared.get("treaties", {}).get(t) or {}).get("zh") or (ctx.shared.get("treaties", {}).get(t) or {}).get("en") or t}
                         for t in a.get("treaties", [])],
            "curated": bool(a.get("curated"))}


@router.get("/api/state/{sid}")
def state(sid: str):
    R = resolver(_ctx())
    s = R.states.get(sid)
    if not s:
        raise HTTPException(404, "没有这个政权")
    return {"id": sid, "name": _zh_disp(s.get("zh") or s.get("en")), "en": s.get("en"), "desc": s.get("desc"),
            "from": _t(s.get("from")), "to": _t(s.get("to")), "summary": wiki.summary(s.get("zhwiki"), s.get("enwiki"))}


_pn_cache = []


def _PN():
    if not _pn_cache:
        p = _ctx().data_dir / "polity_names.json"
        _pn_cache.append(json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})
    return _pn_cache[0]


@router.get("/api/snapshot_names/{snap}")
def snapshot_names(snap: str, date: str | None = None):
    """该快照每个多边形在快照年份对应的政权中文名（来自解析到的 Wikidata 政权，只取「强」候选）。
    用于地图悬停提示和面板标题，避免把现代国名（如「中华人民共和国」）套到历史时期。"""
    from .geo import norm_snap
    R = resolver(_ctx())
    snap = norm_snap(snap)
    if date:
        d = parse_date(date)
    elif isinstance(snap, str):
        d = _ctx().basemaps.trans.parse(snap)[1]
    else:
        d = HDate(snap if snap != 0 else 1, 0, 0)
    out = {}
    for fid in _ctx().basemaps.features(snap):
        cands = R.resolve(snap, fid, d)
        c = R.primary(cands, d)
        lab = _ctx().basemaps.features(snap)[fid]["props"].get("LABEL_ZH")
        if c and lab:
            out[str(fid)] = {"zh": lab, "qid": c["state"]["id"], "method": c["method"]}
        elif c and c["method"] == "owner":
            # CShapes 殖民地/保护国/托管地，本身没有对应的 Wikidata 条目：显示「地区名（宗主国 + 地位）」
            props = _ctx().basemaps.features(snap)[fid]["props"]
            gi = _ctx().basemaps.cs.gw.get(props.get("CSHAPES"), {})
            modern = (R.states.get((gi.get("ne") or [None])[0]) or {}).get("zh")
            own = c["state"].get("zh") or c["state"].get("en")
            if not modern:   # v0.6.1：多边形原名的中文名（polity_names / 中文维基链接名），没有的标「暂无通用译名」
                from .zh import basemap_names
                nm0 = props.get("NAME")
                modern = (_PN().get(nm0) or {}).get("zh") or basemap_names(_ctx().data_dir).get(nm0) or _zh_disp(nm0)
            out[str(fid)] = {"zh": f'{modern}（{own}{props.get("STATUS_ZH") or "属地"}）', "qid": c["state"]["id"], "method": "owner"}
        elif c and (c["state"].get("zh") or c["state"].get("en")):
            out[str(fid)] = {"zh": _zh_disp(c["state"].get("zh") or c["state"]["en"]), "qid": c["state"]["id"], "method": c["method"]}
        elif R.split_names(cands) and d.y >= -500:
            # 已分裂：旧政权解散后由几个政权分有，底图边界要到下一张快照才更新
            out[str(fid)] = {"kind": "split", "parts": R.split_names(cands)[:5]}
        else:
            # 没有当时存在的政权：史前/上古多为考古文化或人群分布，标为「文化/地区」
            out[str(fid)] = {"kind": "culture" if d.y < -500 or not cands else "region"}
        # 底图原名的中文译名（polity_names.json 或 zh_basemap_names.json：英文维基同名条目的中文维基链接）；没有的标「暂无通用译名」
        if "zh" not in out[str(fid)]:
            from .zh import basemap_names, disp
            nm = _ctx().basemaps.features(snap)[fid]["props"].get("NAME")
            pn = (_PN().get(nm) or {}).get("zh") or basemap_names(_ctx().data_dir).get(nm)
            out[str(fid)]["title"] = pn or disp(nm)
    return out


@router.get("/api/polity_states")
def polity_states(snap: str, fid: int, date: str):
    R = resolver(_ctx())
    d = parse_date(date)
    return [{"id": c["state"]["id"], "name": _zh_disp(c["state"].get("zh") or c["state"].get("en")), "method": c["method"],
             "method_zh": METHOD_ZH.get(c["method"], c["method"]), "score": c["score"]}
            for c in R.resolve(snap, fid, d)]


def _stored_summary(r):
    """tools/enrich_text.py 预先取得的维基百科导言（离线可用）；英文导言附机器翻译。"""
    sm = r.get("summary")
    if not sm or not (sm.get("text") or sm.get("en")):
        return None
    zh = sm.get("src") == "zh.wikipedia"
    return {"lang": "zh" if zh else "en", "title": r.get("zhwiki") if zh else r.get("enwiki"),
            "extract": sm.get("text") or sm.get("en"), "orig": None if zh else sm.get("en"), "mt": bool(sm.get("mt")),
            "url": sm.get("url"), "thumb": None}


@router.get("/api/treaty/{tid}")
def treaty(tid: str):
    """条约详情：日期、全部签署方、维基百科摘要（中文优先）、维基文库/全文链接。"""
    from .modules.spirits import kind_of, tend, tstart
    ctx = _ctx()
    R = resolver(ctx)
    r = ctx.shared.get("treaties", {}).get(tid)
    if not r:
        raise HTTPException(404, "没有这个条约")
    VIA = {"P1891": "签署方", "P710": "参与方", "P17": "所属国家（P17）", "P1268": "签署人所代表的国家",
           "P1268+P35": "签署人（当时的国家元首）所代表的国家"}
    parties = []
    for p in r.get("parties", []):
        x = {"id": p["s"], "name": R.state_name(p["s"]), "via": VIA.get(p["via"], p["via"])}
        if p.get("rep"):
            x["rep"] = R.person_brief(p["rep"])
        parties.append(x)
    links = [{"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{tid}"}]
    for fld, label, base in (("zhwiki", "中文维基", "https://zh.wikipedia.org/wiki/"), ("enwiki", "English Wikipedia", "https://en.wikipedia.org/wiki/"),
                             ("zhws", "维基文库（中文原文）", "https://zh.wikisource.org/wiki/"), ("enws", "Wikisource（英文原文）", "https://en.wikisource.org/wiki/")):
        if r.get(fld):
            links.append({"label": label, "url": base + r[fld].replace(" ", "_")})
    if r.get("fulltext"):
        links.append({"label": "全文（P953）", "url": r["fulltext"]})
    others = r.get("other_P1891", 0) + r.get("other_P710", 0)
    return {"id": tid, "name": _zh_disp(r.get("zh") or r.get("en")), "en": r.get("en"), "desc": r.get("desc"), "kind": kind_of(r),
            "types": [t.get("zh") or t.get("en") for t in r.get("types", [])],
            "signed": _t(r.get("signed")), "effective": _t(r.get("effective")), "start": _t(r.get("start") or r.get("inception")),
            "end": _t(tend(r)), "parties": parties, "others": others,
            "summary": _stored_summary(r) or wiki.summary(r.get("zhwiki"), r.get("enwiki")), "links": links,
            "location": [{"name": _zh_disp(x.get("zh") or x.get("en")), "coord": x.get("coord")} for x in r.get("location", [])],
            "countries": [R.state_name(c) for c in r.get("countries", [])],
            "name_mt": bool(r.get("zh_mt")),
            "has_text": bool(r.get("zhws") or r.get("enws") or r.get("fulltext"))}
