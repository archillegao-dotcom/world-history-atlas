#!/usr/bin/env python3
"""国旗审计（前 60）：1800–2026 每年 7 月 1 日，统计地图上出现年份最多的 60 个政权；对每个政权在出现的每一年调用 flag_at（与面板同规则），
统计「有日期依据 / 无日期语句（可能与年代不符）/ 无国旗」年数，并列出首年、中间、末年所用文件供人工核对。
→ data/audit/flags_top60.json / .md"""
import collections, json, sys, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa
from backend.geo import BasemapStore  # noqa
from backend.polity import PolityResolver  # noqa
from backend.flags import flag_at  # noqa
from backend.timeutil import HDate  # noqa
B = BasemapStore(); R = PolityResolver(config.DATA_DIR); R.geo = B
seen = collections.defaultdict(set)
for y in range(1800, 2027):
    d = HDate(y, 7, 1); snap = B.snapshot_at(d)
    for fid in B.features(snap):
        p = R.primary(R.resolve(snap, fid, d), d)
        st = (p or {}).get("state") or {}
        if st.get("id") in R.states:
            seen[st["id"]].add(y)
top = sorted(seen, key=lambda q: -len(seen[q]))[:60]
rows = []
for q in top:
    st = R.states[q]; ys = sorted(seen[q]); c = collections.Counter(); files = {}
    for y in ys:
        f, dated, _, note = flag_at(config.DATA_DIR, [st], HDate(y, 7, 1).key())
        k = "dated" if f and dated else ("undated" if f else "none"); c[k] += 1
        files.setdefault(f or "—", []).append(y)
    rows.append({"qid": q, "name": st.get("zh") or st.get("en"), "years": len(ys), "first": ys[0], "last": ys[-1], **c,
                 "files": {urllib.parse.unquote(k): [v[0], v[-1], len(v)] for k, v in files.items()}})
json.dump(rows, open(ROOT / "data/audit/flags_top60.json", "w"), ensure_ascii=False, indent=1)
with open(ROOT / "data/audit/flags_top60.md", "w") as f:
    n = sum(r["years"] for r in rows); dd = sum(r.get("dated", 0) for r in rows); ud = sum(r.get("undated", 0) for r in rows); no = sum(r.get("none", 0) for r in rows)
    f.write(f"# 国旗审计：1800–2026 地图出现年份最多的 60 个政权\n\n由 tools/audit_flags_top60.py 生成（每年 7 月 1 日）。政权-年共 {n}：有日期依据 {dd}（{dd/n:.1%}），只有无日期语句 {ud}（{ud/n:.1%}，需人工核对年代），无国旗 {no}（{no/n:.1%}）。\n\n")
    f.write("| 政权 | QID | 出现年份 | 有日期 | 无日期 | 无旗 | 所用文件（首年–末年，年数） |\n|---|---|---|---|---|---|---|\n")
    for r in rows:
        fs = "；".join(f"{k}（{a}–{b}，{c}）" for k, (a, b, c) in r["files"].items())
        f.write(f"| {r['name']} | {r['qid']} | {r['first']}–{r['last']}（{r['years']}） | {r.get('dated', 0)} | {r.get('undated', 0)} | {r.get('none', 0)} | {fs} |\n")
print("done", len(rows))
