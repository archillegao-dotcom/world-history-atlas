"""空位期 / 共治 / 摄政验收（v0.6.1）
1. 中国逐年：公元前 841 年至 1912 年每年 7 月 1 日，依次在西安、洛阳、南京、杭州、北京点选（与面板同一路径：/api/locate → /api/modules/leaders），
   只要有一处领导人面板给出人物（国家元首、在任职位、或「实际掌权者」）即算有领导人。目标：没有领导人的年份 = 0。
2. data/curated/interregna.json 中每个案例：在其 probe 日期与地点点选，面板必须显示该案例，且至少有一位掌权者（个案本身没有列掌权者的空位期除外）。
3. 全世界缺口扫描（数据层面）：Wikidata 君主类职位（国王/皇帝/苏丹/沙皇/君主……）在政权存续期内、相邻两任之间超过 90 天的空档，
   列出是否已由案例覆盖 → data/audit/leader_gaps.md（供人工继续补充；不计入通过率）。
用法：.venv/bin/python tools/accept/interregna.py → logs/interregna.json、data/audit/interregna.md、data/audit/leader_gaps.md"""
import json, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, ".")
B = "http://127.0.0.1:8792"
PTS = [("西安", 34.26, 108.94), ("洛阳", 34.62, 112.45), ("南京", 32.06, 118.8), ("杭州", 30.27, 120.15), ("北京", 39.9, 116.4)]

def get(p, **kw):
    return json.load(urllib.request.urlopen(B + p + "?" + urllib.parse.urlencode(kw), timeout=300))

def ds(y, md="07-01"):
    return f"{'-' if y < 0 else ''}{abs(y):04d}-{md}"

def panel(d, la, lo, state=None):
    loc = get("/api/locate", date=d, lat=la, lon=lo); p = loc.get("polity")
    if not p:
        return None, None
    kw = {"state": state} if state else {}
    L = get("/api/modules/leaders", date=d, snap=loc["snapshot"], fid=p["fid"], **kw)
    return p, L

def people(L):
    out = [("元首", h["person"].get("name")) for h in L.get("heads", []) if h.get("person")]
    out += [(o["office"]["name"], h["person"].get("name")) for o in L.get("offices", []) for h in o.get("holders", []) if h.get("person")]
    out += [(f'{c["kind"]}·{x["tag"]}', x["person"].get("name")) for c in L.get("interregna", []) for x in c["leaders"]]
    return out

def china(y):
    d = ds(y); tried = []
    for nm, la, lo in PTS:
        try:
            p, L = panel(d, la, lo)
            if not p:
                tried.append(f"{nm}:无多边形"); continue
            ps = people(L)
            if ps:
                return {"y": y, "ok": True, "where": nm, "state": (L.get("state") or {}).get("name"), "who": ps[:3],
                        "inter": [c["id"] for c in L.get("interregna", [])]}
            tried.append(f"{nm}:{(L.get('state') or {}).get('name') or p.get('NAME')}无领导人")
        except Exception as e:
            tried.append(f"{nm}:{repr(e)[:80]}")
    return {"y": y, "ok": False, "tried": tried}

def case(c):
    pr = c["probe"]
    if c.get("nomap"):
        return {"id": c["id"], "title": c["title"], "ok": None, "nomap": c["nomap"], "why": "地图无该政权独立多边形（不计入）"}
    try:
        p, L = panel(pr["date"], pr["lat"], pr["lon"])
    except Exception as e:
        return {"id": c["id"], "ok": False, "why": repr(e)[:100]}
    if not p:
        return {"id": c["id"], "ok": False, "why": "无多边形"}
    hit = [x for x in L.get("interregna", []) if x["id"] == c["id"]]
    via = None
    if not hit:   # v0.6.1：个案所属政权在面板「其他可能的政权」下拉中时，像用户一样切换过去再看
        alts = [a["id"] for a in L.get("alternatives", [])]
        for s in c["states"]:
            if s in alts:
                _, L2 = panel(pr["date"], pr["lat"], pr["lon"], state=s)
                hit = [x for x in L2.get("interregna", []) if x["id"] == c["id"]]
                if hit:
                    L, via = L2, s
                    break
    # v0.6.1：史料没有公认单一掌权者的空位期（个案 leaders 为空，说明里写明由议会/选帝侯理政），只要求面板显示该个案
    ok = bool(hit and (hit[0]["leaders"] or not c["leaders"]))
    return {"id": c["id"], "title": c["title"], "ok": ok, "state": (L.get("state") or {}).get("name"), "date": pr["date"],
            "leaders": [f'{x["tag"]}:{x["person"]["name"]}' for x in hit[0]["leaders"]] if hit else [],
            "alt": bool(hit and hit[0].get("alt")), "via_state": via, "why": None if ok else "面板没有显示该案例"}

MON = re.compile(r"(?i)\b(king|queen regnant|emperor|empress regnant|sultan|tsar|czar|shah|caliph|pharaoh|monarch|khagan|khan)\b")
MON_X = re.compile(r"(?i)consort|prince|crown|heir|viceroy|vassal|titular|pretender|claimant|anti|dowager|mother|spouse|wife")

def gaps():
    from backend import config
    from backend.polity import PolityResolver, lifespan
    from backend.timeutil import rec_key
    from backend.interregna import _cases, valid_at as iv
    from backend.timeutil import HDate
    R = PolityResolver(config.DATA_DIR)
    cases = _cases(config.DATA_DIR)
    rows = []
    for q, offs in R.office_by_state.items():
        st = R.states.get(q)
        if not st:
            continue
        a, b, _ = lifespan(st)
        ka, kb = rec_key(a), rec_key(b) if b else 2100
        for o in offs:
            en = o.get("en") or ""
            if not MON.search(en) or MON_X.search(en) or not o.get("holders"):
                continue
            iv_ = sorted(((rec_key(h["from"]), rec_key(h["to"]) if h.get("to") else None, h["p"]) for h in o["holders"]
                          if h.get("from") and h["from"].get("m")), key=lambda x: x[0])
            if len(iv_) < 3:
                continue
            reach = None
            for s, e, p in iv_:
                if reach is not None and s - reach > 0.25 and (ka is None or s > ka) and reach < kb:
                    mid = (s + reach) / 2
                    y = int(mid) if mid >= 0 else int(mid) - 1
                    cov = [c["id"] for c in cases if q in c["states"] and iv(HDate(y, 7, 1).key(), c["from"], c["to"])]
                    rows.append({"state": q, "state_zh": st.get("zh") or st.get("en"), "office": o.get("zh") or en,
                                 "from": round(reach, 2), "to": round(s, 2), "years": round(s - reach, 2), "covered": cov,
                                 "next": R.persons.get(p, {}).get("zh") or R.persons.get(p, {}).get("en")})
                if e is None:
                    reach = None if reach is None else max(reach, s); continue
                reach = e if reach is None else max(reach, e)
    rows.sort(key=lambda r: -r["years"])
    return rows

if __name__ == "__main__":
    from backend import config
    from backend.interregna import _cases
    C = _cases(config.DATA_DIR)
    ys = [y for y in range(-841, 1913) if y != 0]
    with ThreadPoolExecutor(6) as ex:
        ch = list(ex.map(china, ys))
        cs = list(ex.map(case, C))
    miss = [r for r in ch if not r["ok"]]
    json.dump({"china": ch, "cases": cs}, open("logs/interregna.json", "w"), ensure_ascii=False, indent=0)
    try:
        g = gaps()
    except Exception as e:
        print("gap scan failed", repr(e)); g = []
    json.dump({"china": ch, "cases": cs, "gaps": g}, open("logs/interregna.json", "w"), ensure_ascii=False, indent=0)
    nci = sum(1 for r in ch if r["ok"] and r.get("inter"))
    csm = [c for c in cs if c.get("nomap")]; cs_t = [c for c in cs if not c.get("nomap")]   # 无独立多边形的个案单列
    with open("data/audit/interregna.md", "w") as f:
        f.write(f"# 空位期 / 共治 / 摄政验收\n\n由 tools/accept/interregna.py 生成。\n\n"
                f"- 中国逐年（前841–1912，每年 7 月 1 日）：有领导人 {len(ch) - len(miss)}/{len(ch)}；其中由「实际掌权者」案例给出或同时给出的 {nci} 年。\n"
                f"- 案例：{sum(1 for c in cs_t if c['ok'])}/{len(cs_t)} 在面板中显示；另有 {len(csm)} 个个案所属政权在地图上没有独立多边形（只在数据层面，不计入）。\n\n## 没有领导人的年份\n\n" +
                ("（无）\n" if not miss else "".join(f"- {r['y']}：{'；'.join(r['tried'])}\n" for r in miss)) +
                "\n## 案例\n\n| 案例 | 日期 | 政权 | 掌权者 | 另一说 | 结果 |\n|---|---|---|---|---|---|\n" +
                "".join(f"| {c.get('title', c['id'])} | {c.get('date', '')} | {c.get('state') or ''} | {'；'.join(c.get('leaders', []))} | {'有' if c.get('alt') else ''} | {'通过' if c['ok'] else ('不计入：' + c['nomap']) if c.get('nomap') else '失败：' + (c.get('why') or '')} |\n" for c in cs))
    with open("data/audit/leader_gaps.md", "w") as f:
        f.write("# 全世界君主任职空档扫描（数据层面）\n\n由 tools/accept/interregna.py 生成：Wikidata 君主类职位相邻两任之间超过 3 个月的空档（任期至少精确到月）。"
                "多数是 Wikidata 任职记录不全，不一定是真实的空位期；「已覆盖」表示该时段已有人工整理的实际掌权者案例。\n\n"
                f"共 {len(g)} 处；已覆盖 {sum(1 for r in g if r['covered'])} 处。\n\n"
                "## 5 年以内的空档（较可能是真实的空位期或交接，优先人工核对）\n\n| 政权 | 职位 | 空档（年） | 长度（年） | 下一任 | 已覆盖 |\n|---|---|---|---|---|---|\n" +
                "".join(f"| {r['state_zh']} | {r['office']} | {r['from']:.2f}–{r['to']:.2f} | {r['years']} | {r['next'] or ''} | {'、'.join(r['covered'])} |\n" for r in sorted(g, key=lambda r: r['from']) if r['years'] <= 5) +
                "\n## 全部（按长度）\n\n| 政权 | 职位 | 空档（年） | 长度（年） | 下一任 | 已覆盖 |\n|---|---|---|---|---|---|\n" +
                "".join(f"| {r['state_zh']} | {r['office']} | {r['from']:.1f}–{r['to']:.1f} | {r['years']} | {r['next'] or ''} | {'、'.join(r['covered'])} |\n" for r in g))
    print(f"CHINA {len(ch) - len(miss)}/{len(ch)} (via interregna {nci}); CASES {sum(1 for c in cs_t if c['ok'])}/{len(cs_t)} (+{len(csm)} nomap); GAPS {len(g)} covered {sum(1 for r in g if r['covered'])}")
    for r in miss[:60]:
        print("MISS", r["y"], r["tried"][:3])
    for c in cs_t:
        if not c["ok"]:
            print("CASEFAIL", c)
