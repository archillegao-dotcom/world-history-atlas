#!/usr/bin/env python3
"""界面可见文字的中文覆盖率 → data/audit/translation_coverage.json
对条约、政权、职位、阵营（及人物、事件作参考）统计：名称 / 描述 / 简介 是「原生中文」（Wikidata 中文标签、中文维基）、
「机器翻译」（tools/enrich_text.py 标注的「（译名）」「（机器翻译）」）还是「没有中文」（界面显示英文或「未记录」）。
政权另统计「地图上会用到的」子集（polity_map 中出现过的候选）。"""
import datetime, gzip, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config
D = config.DATA_DIR
CJK = re.compile(r"[\u4e00-\u9fff]")


def load(n):
    return json.load(gzip.open(D / n, "rt", encoding="utf-8"))


def name_cls(r):
    z = r.get("zh") or ""
    if not CJK.search(z):
        return "none"
    if r.get("zh_mt") or r.get("name_mt") or z.endswith("（译名）"):
        return "mt"
    return "native"


def desc_cls(r):
    d = r.get("desc") or ""
    if not d:
        return "empty"
    if r.get("desc_mt") or d.endswith("（机器翻译）"):
        return "mt"
    return "native" if CJK.search(d) else "none"


def summ_cls(r):
    s = r.get("summary") or {}
    if not s.get("text"):
        return "empty"
    if s.get("mt") or s.get("src") != "zh.wikipedia":
        return "mt" if CJK.search(s["text"]) else "none"
    return "native"


def tally(recs, f):
    c = {"native": 0, "mt": 0, "none": 0, "empty": 0}
    for r in recs:
        c[f(r)] += 1
    n = len(recs) or 1
    return {**c, "total": len(recs), "zh_pct": round(100 * (c["native"] + c["mt"]) / n, 1), "native_pct": round(100 * c["native"] / n, 1),
            "mt_pct": round(100 * c["mt"] / n, 1)}


def main():
    states = load("states.json.gz")
    pm = load("polity_map.json.gz")
    used = {q for snap in pm.values() for cs in snap.values() for q, *_ in cs}
    offices = load("offices.json.gz") + load("rulers.json.gz")["offices"]
    treaties, alliances = load("treaties.json.gz"), load("alliances.json.gz")
    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds"), "sets": {}}
    sets = {"条约": treaties, "政权（全部）": states, "政权（地图用到的）": [s for s in states if s["id"] in used],
            "职位": offices, "阵营": alliances}
    for k, recs in sets.items():
        out["sets"][k] = {"name": tally(recs, name_cls), "desc": tally(recs, desc_cls)}
        if k in ("条约", "阵营"):
            out["sets"][k]["summary"] = tally(recs, summ_cls)
    for k, n in (("人物（领导人）", "persons.json.gz"), ("事件", "events.json.gz")):
        recs = load(n)
        for r in recs:
            if "zh" not in r and "name" in r:
                r = r
        out["sets"][k] = {"name": tally([{**r, "zh": r.get("zh") or r.get("name")} for r in recs], name_cls), "desc": tally(recs, desc_cls)}
    (D / "audit" / "translation_coverage.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in out["sets"].items():
        print(k, {kk: (vv["total"], f"中文 {vv['zh_pct']}%（原生 {vv['native_pct']}%，机译 {vv['mt_pct']}%）", f"无 {vv['none']}", f"空 {vv['empty']}") for kk, vv in v.items()})


if __name__ == "__main__":
    main()
