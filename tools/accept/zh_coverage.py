"""中文名覆盖检查（任务 C，v0.6.1）
A. 数据层：各数据文件中会显示给用户的名称字段（政权、人物、职位、机构、城市、条约、事件、人物页、同盟、领土、控制区、战线、底图名称），
   统计没有汉字的条目（应用 data/curated/zh_labels.json 与 zh_basemap_names.json 之后，用 --raw 统计应用之前）。
B. 接口层：抽样日期（前3000 年起每 25 年；1939-01 至 1945-12 每月；2020-06-01；2026-11-01）调用与前端相同的接口：
   多边形标题（/api/snapshot_names + 底图名）、城市/控制区/战线图层标签、每个日期 6 个多边形的政权/领导人面板，3 个多边形的事件/政治人物列表。
   主标签没有汉字、或以英文开头再括号中文的，记为未翻译；带「暂无通用译名」标记的单独计数。
用法：.venv/bin/python tools/accept/zh_coverage.py TAG [--raw] [--data-only] → logs/zh_coverage_TAG.json、data/audit/zh_coverage_TAG.md"""
import json, os, re, sys, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
from backend.datafile import read_json
CJK = re.compile(r"[\u4e00-\u9fff]"); NOTR = "暂无通用译名"
B = "http://127.0.0.1:8792"; D = Path("data")
TAG = sys.argv[1]; RAW = "--raw" in sys.argv
def ok(s):
    return bool(s) and bool(CJK.search(s)) and not re.match(r"^[A-Za-z][^（]*（[^）]*[\u4e00-\u9fff]", s)
def bad(s):
    return s is not None and str(s).strip() != "" and not ok(str(s))
stat = collections.defaultdict(lambda: [0, 0, 0, []])   # 类别 → [总数, 未翻译, 标「暂无通用译名」, 例子]
def add(cat, s, ident=""):
    s = (s or "").strip()
    if not s:
        return
    st = stat[cat]; st[0] += 1
    if NOTR in s:
        st[2] += 1
    elif bad(s):
        st[1] += 1
        if len(st[3]) < 12:
            st[3].append(f"{s}{' ' + ident if ident else ''}")
def data_layer():
    lab = {} if RAW else {**json.loads((D / "curated/zh_labels.json").read_text())["labels"], **json.loads((D / "curated/zh_manual.json").read_text())["labels"]}
    bm = {} if RAW else (json.loads((D / "curated/zh_basemap_names.json").read_text())["names"] if (D / "curated/zh_basemap_names.json").exists() else {})
    sys.path.insert(0, ".")
    if RAW:
        os.environ["WHA_ZH_RAW"] = "1"
    from backend import zh as Z   # 与运行时同一套补译/标注逻辑
    def nm(r, f="zh"):
        v = r.get(f)
        if not CJK.search(v or "") and RAW:
            return v or r.get("en") or r.get("en_name") or r.get("name")
        return Z.disp(v or r.get("en" if f == "zh" else "en_name"))
    for f, cat in [("states", "数据·政权"), ("persons", "数据·人物（领导人）"), ("ruler_persons", "数据·君主"), ("offices", "数据·职位"), ("orgs", "数据·机构"),
                   ("cities", "数据·城市"), ("treaties", "数据·条约"), ("alliances", "数据·同盟")]:
        recs = read_json(D / f"{f}.json.gz", [])
        Z.fill(recs, D)
        for r in recs:
            add(cat, nm(r), r.get("id"))
    for f, cat in [("events", "数据·事件"), ("people_politician", "数据·政治人物"), ("people_writer", "数据·文学家"), ("people_philosopher", "数据·哲学家")]:
        recs = read_json(D / f"{f}.json.gz", [])
        Z.fill(recs, D, "name")
        for r in recs:
            add(cat, nm(r, "name"), r.get("id"))
    for r in read_json(D / "territories.json.gz", []):
        add("数据·特殊领土", r.get("name_zh") or r.get("name"))
    for z in json.loads((D / "curated/control_zones.json").read_text())["zones"]:
        add("数据·控制区标签", z.get("name_zh") or z.get("name_en"), z["id"])
    rs = json.loads((D / "curated/runtime_states.json").read_text())
    for q, r in rs.items():
        if q.startswith("Q"):
            Z.fill([r], D)
            add("数据·补充政权", nm(r), q)
    for n, v in json.loads((D / "polity_names.json").read_text()).items():
        if n.strip():
            add("数据·底图名称", v.get("zh") or (bm.get(n) or {}).get("zh") or (n if RAW else Z.disp(n)))
def get(p, **kw):
    import gzip
    b = urllib.request.urlopen(B + p + ("?" + urllib.parse.urlencode(kw) if kw else ""), timeout=600).read()
    return json.loads(gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b)
def dates():
    ds = [f"{'-' if y < 0 else ''}{abs(y):04d}-07-01" for y in range(-3000, 2026, 25) if y != 0]
    ds += [f"{y}-{m:02d}-15" for y in range(1939, 1946) for m in range(1, 13)]
    return ds + ["2020-06-01", "2026-11-01"]
_bm = {}
def one(d):
    out = []
    try:
        s = get("/api/snapshot", date=d); snap = s["snapshot"]
        names = get(f"/api/snapshot_names/{snap}", date=d)
        if snap not in _bm:
            _bm[snap] = {str(f["properties"]["fid"]): f["properties"] for f in get(f"/api/basemap/{snap}")["features"]}
        props = _bm[snap]
        for fid, z in names.items():
            p = props.get(fid, {})
            t = z.get("zh") if z.get("zh") else (p.get("NAME_ZH") if p.get("TERRITORY") and p.get("NAME_ZH") else (z.get("title") or p.get("NAME_ZH_DISPLAY") or p.get("NAME")))
            out.append(("接口·地图多边形标题", t, f"{d} {p.get('NAME')}"))
        for l, f in [("cities", "name"), ("control_zones", "name"), ("war_fronts", "name")]:
            for it in get(f"/api/layers/{l}", date=d).get("items", []):
                out.append((f"接口·图层·{l}", it.get(f), d))
        fids = [fid for fid, z in names.items() if z.get("qid")]
        fids = fids[:: max(1, len(fids) // 6)][:6]
        for k, fid in enumerate(fids):
            q = dict(date=d, snap=snap, fid=fid)
            R = get("/api/modules/regime", **q)
            out.append(("接口·面板·政权名", (R.get("state") or {}).get("name"), d))
            for c in R.get("capital") or []:
                out.append(("接口·面板·首都", c, d))
            for c in ((R.get("chain") or {}).get("now") or []):
                out.append(("接口·面板·所选日期的政权", c, d))
            L = get("/api/modules/leaders", **q)
            for h in L.get("heads", []):
                out.append(("接口·面板·元首/首脑", h["person"].get("name"), d))
            for o in L.get("offices", []):
                out.append(("接口·面板·职位名", o["office"].get("name"), d))
                for h in o["holders"]:
                    out.append(("接口·面板·任职者", h["person"].get("name"), d))
            for c in L.get("interregna", []):
                for x in c["leaders"]:
                    out.append(("接口·面板·实际掌权者", x["person"].get("name"), d))
            if k < 3:
                for mid, cat in [("events", "接口·事件"), ("people_politician", "接口·政治人物")]:
                    for it in get(f"/api/modules/{mid}", **q).get("items", [])[:15]:
                        out.append((cat, it.get("title"), d))
    except Exception as e:
        out.append(("接口·错误", "ERR " + repr(e)[:80], d))
    return out
if __name__ == "__main__":
    data_layer()
    if "--data-only" not in sys.argv:
        with ThreadPoolExecutor(4) as ex:
            for res in ex.map(one, dates()):
                for cat, s, ident in res:
                    add(cat, s, ident)
    rows = sorted(stat.items())
    tot = [sum(v[i] for k, v in rows if k.startswith(p)) for p in ("数据", "接口") for i in (0, 1, 2)]
    json.dump({k: {"total": v[0], "untranslated": v[1], "marked": v[2], "examples": v[3]} for k, v in rows}, open(f"logs/zh_coverage_{TAG}.json", "w"), ensure_ascii=False, indent=1)
    with open(f"data/audit/zh_coverage_{TAG}.md", "w") as f:
        f.write(f"# 中文名覆盖（{TAG}{'，未应用补译' if RAW else ''}）\n\n由 tools/accept/zh_coverage.py 生成。\n\n"
                f"- 数据层：{tot[0]} 个名称，未翻译 {tot[1]}（{tot[1] / max(tot[0], 1):.1%}），标「暂无通用译名」{tot[2]}\n"
                f"- 接口层（抽样日期）：{tot[3]} 个显示字符串，未翻译 {tot[4]}（{tot[4] / max(tot[3], 1):.1%}），标「暂无通用译名」{tot[5]}\n\n"
                "| 类别 | 总数 | 未翻译 | 标「暂无通用译名」 | 覆盖率 | 例子 |\n|---|---|---|---|---|---|\n" +
                "".join(f"| {k} | {v[0]} | {v[1]} | {v[2]} | {(v[0] - v[1]) / max(v[0], 1):.1%} | {'；'.join(v[3][:6])} |\n" for k, v in rows))
    print(f"DATA {tot[0]} untranslated {tot[1]} marked {tot[2]}; API {tot[3]} untranslated {tot[4]} marked {tot[5]}")
    for k, v in rows:
        print(f"{k}: {v[0]} / bad {v[1]} / marked {v[2]}  e.g. {v[3][:3]}")
