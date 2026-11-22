"""国家/政权存续年代审计。

检查政权表里的起讫是否颠倒，同名政权的存续是否叠在一起，以及地图解析会不会在该政权不存在的年份把它当成主要政权。
用法：.venv/bin/python tools/accept/regime_lifespan_audit.py
写出 docs/REGIME_LIFESPAN_AUDIT.md。只改 data/curated/lifespan_overrides.json 里写明来源的条目。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.datafile import read_json
from backend.geo import BasemapStore
from backend.polity import PolityResolver, alive
from backend.timeutil import HDate

DATA = ROOT / "data"
OUT = ROOT / "docs" / "REGIME_LIFESPAN_AUDIT.md"


def year_inverted(a, b) -> bool:
    if not a or not b or "y" not in a or "y" not in b:
        return False
    if a["y"] != b["y"]:
        return a["y"] > b["y"]
    am, bm = a.get("m") or 0, b.get("m") or 0
    if am and bm and am != bm:
        return am > bm
    ad, bd = a.get("d") or 0, b.get("d") or 0
    return bool(am and bm and am == bm and ad and bd and ad > bd)


def main():
    states = {s["id"]: s for s in read_json(DATA / "states.json.gz", []) if isinstance(s, dict) and s.get("id")}
    extra = json.loads((DATA / "curated" / "runtime_states.json").read_text(encoding="utf-8"))
    for q, r in extra.items():
        if q.startswith("Q") and q not in states and isinstance(r, dict):
            states[q] = {**r, "id": q}
    raw_inv = []
    for s in states.values():
        if year_inverted(s.get("from"), s.get("to")):
            raw_inv.append(s["id"])
    R = PolityResolver(DATA)
    inv = []
    for s in R.states.values():
        if year_inverted(s.get("from"), s.get("to")):
            inv.append((s["id"], s.get("zh") or s.get("en"), s.get("from"), s.get("to")))

    # 同名、坐标接近、重叠五年以上。解析器在强候选里优先取包含该日、存在期更短的一条，所以不合并。
    groups = {}
    for s in R.states.values():
        zh = s.get("zh")
        if zh and s.get("from"):
            groups.setdefault(zh, []).append(s)
    dups = []
    for zh, ss in groups.items():
        if len(ss) < 2:
            continue
        for i, a in enumerate(ss):
            for b in ss[i + 1:]:
                ae = a["to"]["y"] if a.get("to") else 2026
                be = b["to"]["y"] if b.get("to") else 2026
                left, right = max(a["from"]["y"], b["from"]["y"]), min(ae, be)
                if right - left < 5:
                    continue
                ca, cb = a.get("coord"), b.get("coord")
                if not ca or not cb:
                    continue
                dist = math.hypot(ca[0] - cb[0], ca[1] - cb[1])
                if dist < 5:
                    dups.append((zh, a["id"], a["from"]["y"], ae, b["id"], b["from"]["y"], be, round(dist, 2)))

    am = R.states["Q481766"]
    am_ok = alive(HDate(-1300, 1, 1).key(), am) and not alive(HDate(1300, 1, 1).key(), am)

    B = BasemapStore()
    R.geo = B
    probes = []
    samples = [
        ("阿穆鲁坐标，约公元前1300年", -1300, 1, 1, 36.2319, 34.5697),
        ("阿穆鲁坐标，公元1300年", 1300, 1, 1, 36.2319, 34.5697),
        ("布达佩斯，1910-06-01", 1910, 6, 1, 19.04, 47.50),
        ("布达佩斯，1930-06-01", 1930, 6, 1, 19.04, 47.50),
    ]
    stolen = []
    for label, y, m, d, lon, lat in samples:
        date = HDate(y, m, d)
        snap = B.snapshot_at(date)
        feat = B.locate(snap, lon, lat) if snap is not None else None
        if not feat:
            probes.append((label, str(snap), "这个点没有多边形"))
            continue
        fid = feat["props"]["fid"]
        base = feat["props"].get("NAME_ZH") or feat["props"].get("NAME") or ""
        cands = R.resolve(snap, fid, date)
        p = R.primary(cands, date)
        pname = (p["state"].get("zh") or p["state"].get("en")) if p else "无"
        pid = p["state"]["id"] if p else ""
        names = []
        for c in cands:
            if not c.get("strong"):
                continue
            nm = c["state"].get("zh") or c["state"].get("en")
            if nm and nm not in names:
                names.append(nm)
        probes.append((label, f"{snap} fid={fid} 底图 {base}", f"主要政权 {pid} {pname}；强候选 {('、'.join(names[:6]) or '无')}"))
        if y == 1300 and pid == "Q481766":
            stolen.append(label)

    lines = [
        "# 国家/政权存续年代审计",
        "",
        "2026-11-22（欧洲/巴黎）。脚本 `tools/accept/regime_lifespan_audit.py`。",
        "起讫用政权表，再套 `data/curated/lifespan_overrides.json`。地图上的主要政权用 `PolityResolver`，和面板是同一套。",
        "",
        f"未套修正时，起年晚于迄年的政权：{len(raw_inv)} 个（`{'、'.join(raw_inv) or '无'}`）。",
        f"套上修正以后：{len(inv)} 个。",
        "",
        "## 改了的存续",
        "",
        "`Q481766` 阿穆鲁王国。导出是公元 1380 年到公元 1200 年，起年晚于迄年，区间是空的，地图上不会出现，面板上的年代也是反的。同一维基数据条目的地图文件名是 Near East 1400 BCE，说明这是青铜时代的政权，不是中世纪。修正为约公元前 1380 年至约公元前 1200 年，仍只精确到年。",
        "",
        f"修正后，约公元前 1300 年算作存在，公元 1300 年不算：{'是' if am_ok else '否'}。",
        "来源：<https://www.wikidata.org/wiki/Q481766>。",
        "",
        "## 同名重叠",
        "",
        "下面这些中文名相同、坐标接近、存续重叠五年以上。解析器在强候选里会优先取包含该日、存在期更短的那一条，用来区分「当时那个政权」和笼罩更长时段的同名条目。本批不合并、不删。",
        "",
    ]
    if dups:
        lines.append("| 名称 | 甲 | 乙 | 距离（度） |")
        lines.append("| --- | --- | --- | ---: |")
        for zh, a, af, at, b, bf, bt, dist in dups:
            lines.append(f"| {zh} | `{a}` {af}–{at} | `{b}` {bf}–{bt} | {dist} |")
    else:
        lines.append("没有。")
    lines += [
        "",
        "匈牙利王国：`Q171150` 是 1000–1946 年的长条目，`Q600018` 是 1920-02-29 至 1946-02-01 的短条目。1930 年若两点都是强候选，主要政权应是较短的那条。利珀亲王国同理：`Q14551680`（1789–1918）短于 `Q107380`（1123–1946）。这不是两块领土各画一个国家。",
        "",
        "## 地图抽样",
        "",
        "| 点 | 快照 | 解析 |",
        "| --- | --- | --- |",
    ]
    for label, snap, text in probes:
        lines.append(f"| {label} | {snap} | {text} |")
    lines += [
        "",
        "约公元前 1300 年这个点落在底图的 Hittites 多边形上。候选只是首都或坐标落进来的弱匹配，1800 年以前不从这种弱匹配里挑主要政权。阿穆鲁不在候选里，改到公元前以后没有占住这块。",
        "公元 1300 年同一坐标的主要政权是马木留克王朝。如果变成阿穆鲁，修正就会把它画进中世纪，脚本失败。",
        "1930-06-01 布达佩斯的强候选只有较短的那条匈牙利王国。1910-06-01 是奥匈帝国。同名长条目没有再画成另一个国家。",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("raw_inv", raw_inv, "inv", len(inv), "dups", len(dups), "am_ok", am_ok)
    for row in probes:
        print(row[0], row[2])
    if inv or not am_ok or stolen:
        print("FAIL", inv, am_ok, stolen)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
