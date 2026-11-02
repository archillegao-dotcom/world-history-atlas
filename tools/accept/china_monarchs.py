"""
中国君主逐年覆盖测试：公元前 221 年至 1911 年每年 7 月 1 日，依次在洛阳、西安、南京、杭州、北京点选（经运行中的服务，与面板同一路径），
只要有一处领导人面板给出国家元首即算覆盖；记录政权名、元首、年号。目标：没有元首的年份 = 0。
用法：.venv/bin/python tools/accept/china_monarchs.py → logs/china_monarchs.json + data/audit/china_monarchs.md
"""
import json, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
B = "http://127.0.0.1:8792"
PTS = [("洛阳", 34.62, 112.45), ("西安", 34.26, 108.94), ("南京", 32.06, 118.8), ("杭州", 30.27, 120.15), ("北京", 39.9, 116.4)]

def get(p, **kw):
    return json.load(urllib.request.urlopen(B + p + "?" + urllib.parse.urlencode(kw), timeout=300))

def ds(y):
    return f"{'-' if y < 0 else ''}{abs(y):04d}-07-01"

def one(y):
    d = ds(y); tried = []
    for nm, la, lo in PTS:
        try:
            loc = get("/api/locate", date=d, lat=la, lon=lo); p = loc.get("polity")
            if not p:
                tried.append(f"{nm}:无多边形"); continue
            R = get("/api/modules/regime", date=d, snap=loc["snapshot"], fid=p["fid"]); st = R.get("state") or {}
            L = get("/api/modules/leaders", date=d, snap=loc["snapshot"], fid=p["fid"])
            heads = [h["person"].get("name") for h in L.get("heads", []) if h.get("person")]
            heads += [h["person"].get("name") for o in L.get("offices", []) for h in o.get("holders", []) if h.get("person")]
            eras = [e.get("name") for e in (L.get("eras") or []) if isinstance(e, dict)]
            if heads:
                return {"y": y, "ok": True, "where": nm, "state": st.get("name"), "qid": st.get("id"), "head": heads[0], "eras": eras[:2]}
            # v0.6.1：皇位空缺时由实际掌权者（摄政/权臣/临时执政，data/curated/interregna.json）显示，也算有领导人，单独计数
            inter_l = [f"{x['person'].get('name')}（{x.get('tag')}）" for c in L.get("interregna", []) for x in c.get("leaders", [])]
            if inter_l:
                return {"y": y, "ok": True, "where": nm, "state": st.get("name"), "qid": st.get("id"), "head": inter_l[0], "eras": eras[:2],
                        "via_interregna": [c.get("title") for c in L.get("interregna", [])]}
            tried.append(f"{nm}:{st.get('name') or p.get('NAME')}无元首")
        except Exception as e:
            tried.append(f"{nm}:{repr(e)[:80]}")
    return {"y": y, "ok": False, "tried": tried, "interregnum": interregnum(y)}

def interregnum(y):
    """主朝代的皇帝任职记录在该年前后 2 年内都有人、只是 7 月 1 日恰好空位（前任已卒/被俘、后任未立）→ 有据的空位期，不算数据缺口。"""
    import sys; sys.path.insert(0, ".")
    from backend.timeutil import HDate, rec_key
    R = _R()
    dk = HDate(y, 7, 1).key(); bef = aft = None
    for o in R.offices:
        if o.get("pos") != "Q268218":
            continue
        for h in o.get("holders", []):
            a, b = rec_key(h.get("from")), rec_key(h.get("to"))
            if b is not None and dk - 2 <= b < dk:
                bef = (R.persons.get(h["p"], {}).get("zh"), h.get("to"))
            if a is not None and dk < a <= dk + 2:
                aft = aft or (R.persons.get(h["p"], {}).get("zh"), h.get("from"))
    return {"before": bef, "after": aft} if bef and aft else None

_RR = []
def _R():
    if not _RR:
        import sys; sys.path.insert(0, ".")
        from backend import config
        from backend.polity import PolityResolver
        _RR.append(PolityResolver(config.DATA_DIR))
    return _RR[0]

ys = [y for y in range(-221, 1912) if y != 0]
_R()
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(one, ys))
json.dump(res, open("logs/china_monarchs.json", "w"), ensure_ascii=False, indent=0)
inter = [r for r in res if not r["ok"] and r.get("interregnum")]
miss = [r for r in res if not r["ok"] and not r.get("interregnum")]
ok = len(res) - len(miss) - len(inter)
# 合并连续缺口
spans = []
for r in miss:
    if spans and spans[-1][1] in (r["y"] - 1, -1 if r["y"] == 1 else None):
        spans[-1][1] = r["y"]; spans[-1][2].append(r)
    else:
        spans.append([r["y"], r["y"], [r]])
with open("data/audit/china_monarchs.md", "w") as f:
    f.write(f"# 中国君主逐年覆盖（前221–1911，每年 7 月 1 日）\n\n由 tools/accept/china_monarchs.py 生成。覆盖 {ok}/{len(res)} = {ok / len(res):.1%}；有据空位期 {len(inter)} 年；数据缺口（无元首且非空位期）{len(miss)} 年。\n\n")
    f.write(f"有据空位期 {len(inter)} 年（前任已卒/被俘、后任未立，日期取自 Wikidata 任职记录）：\n\n" + "".join(f"- {r['y']}：前任 {r['interregnum']['before'][0]} 止于 {r['interregnum']['before'][1]}，后任 {r['interregnum']['after'][0]} 始于 {r['interregnum']['after'][1]}\n" for r in inter) + "\n")
    f.write("## 缺口\n\n" + ("（无）\n" if not spans else "".join(f"- {a}–{b}（{len(rs)} 年）：{'；'.join(rs[0]['tried'])}\n" for a, b, rs in spans)))
    f.write("\n## 每 25 年抽样\n\n| 年 | 地点 | 政权 | 元首 | 年号 |\n|---|---|---|---|---|\n")
    for r in res:
        if r["ok"] and r["y"] % 25 == 0:
            f.write(f"| {r['y']} | {r['where']} | {r['state']} | {r['head']} | {'、'.join(x for x in r['eras'] if x) or '—'} |\n")
print(f"COVER {ok}/{len(res)} = {ok / len(res):.1%}; via interregna {sum(1 for r in res if r.get('via_interregna'))} ({', '.join(str(r['y']) for r in res if r.get('via_interregna'))}); interregnum {len(inter)}; data gaps {len(miss)} years in {len(spans)} spans")
for a, b, rs in spans[:40]:
    print(a, b, rs[0]["tried"])
