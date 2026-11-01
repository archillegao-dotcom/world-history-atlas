"""中国抽样表：经由运行中的服务（含过渡层/实际控制区）在 洛阳/杭州/北京 三点查询政权与在位君主。
年份：-2000..1950 每 100 年；180–280、900–1280 每 10 年（取当年 7 月 1 日）。
输出 data/audit/china_table.json 与 data/audit/china_table.md。用法：.venv/bin/python tools/china_table.py [http://127.0.0.1:8792]"""
import json, sys, urllib.request, urllib.parse, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8792"
PTS = {"洛阳": (34.62, 112.45), "杭州": (30.27, 120.15), "北京": (39.9, 116.4)}


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=180))


def cell(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity")
    if not p:
        return {"snap": loc.get("snapshot"), "poly": None, "state": None, "ruler": None}
    d = get("/api/modules/leaders", date=date, snap=loc["snapshot"], fid=p["fid"])
    st = d.get("state") or {}
    ruler = None
    for h in d.get("heads", []):          # 先取国家元首（P35），没有再取第一个有任职者的职位（按重要性排序）
        ruler = (h["role"], h["person"].get("name"))
        break
    if not ruler:
        for o in d.get("offices", []):
            if o.get("holders"):
                ruler = (o["office"]["name"], o["holders"][0]["person"].get("name"))
                break
    return {"snap": loc["snapshot"], "poly": p.get("NAME"), "state": st.get("name"), "qid": st.get("id"),
            "ruler": ruler, "alts": [a["name"] for a in d.get("alternatives", [])[1:4]]}


def date_str(y):
    return (f"-{abs(y):04d}" if y < 0 else f"{y:04d}") + "-07-01"


ys = sorted(set(list(range(-2000, 1951, 100)) + [1950] + list(range(180, 281, 10)) + list(range(900, 1281, 10))) - {0})
rows = []
for y in ys:
    r = {"year": y}
    for k, (la, lo) in PTS.items():
        r[k] = cell(date_str(y), la, lo)
    rows.append(r)
    print(y, {k: (r[k]["state"], r[k]["ruler"]) for k in PTS}, flush=True)
out = ROOT / "data/audit"
(out / "china_table.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
L = ["# 中国抽样表（洛阳 / 杭州 / 北京，各年 7 月 1 日）", "",
     "由 tools/china_table.py 经运行中的服务生成（含过渡层与实际控制区）。格式：政权（地图多边形名）· 国家元首（无则取第一个有任职者的职位）；「—」表示未记录。", "",
     "| 年 | 快照 | 洛阳 | 杭州 | 北京 |", "|---|---|---|---|---|"]
for r in rows:
    def f(c):
        if not c["poly"]:
            return "（无多边形）"
        s = f"{c['state'] or '未匹配'}（{c['poly']}）"
        s += f" · {c['ruler'][1]}" if c["ruler"] else " · —"
        return s
    yl = f"前{-r['year']}" if r["year"] < 0 else str(r["year"])
    L.append(f"| {yl} | {r['洛阳']['snap']} | {f(r['洛阳'])} | {f(r['杭州'])} | {f(r['北京'])} |")
(out / "china_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("rows", len(rows))
