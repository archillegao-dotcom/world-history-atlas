"""
用 Seshat Global History Databank（Equinox-2020 数据包，CC BY-NC-SA 4.0，https://github.com/seshatdb/Equinox_Data）
交叉核对政权存在期。

Seshat 以「NGA（自然地理区域）× 阶段」记录政权，如 "Abbasid Caliphate I"(750–875)。这里把同一政权名称（去掉
罗马数字阶段号、星号、"NGA - " 前缀）的所有阶段合并，取最早开始/最晚结束作为该政权在 Seshat 中的总存在期，
再按英文名/别名与 Wikidata 政权匹配，比较起止年份。

输出 data/xcheck/seshat.json：{wikidata QID: {seshat: [名称, 起, 止, PolID...], diff_start, diff_end, status}}
status: agree（两端相差 ≤50 年）/ conflict（任一端相差 >50 年）。
显示规则（见 README）：显示值仍用 Wikidata（CC0，可再分发）；冲突时在政权面板注明 Seshat 的年份（国际学界数据库），
不改写数据。注意 Seshat 为「非商业」许可：本应用只在非商业用途下附带这份比对结果。
"""
from __future__ import annotations

import collections
import gzip
import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = DATA / "xcheck_raw" / "Equinox_on_GitHub_June9_2022.xlsx"
TOL = 50


def norm(s):
    s = (s or "").lower().strip()
    s = re.sub(r"\s+(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b\.?$", "", s)
    s = s.replace("*", "").strip()
    # 只去掉冠词：保留 empire/kingdom/republic/dynasty 等类型词（否则「Roman Kingdom」会配上「Roman Empire」，
    # 「Dynasty of E」（巴比伦）会配上中国的「鄂国 (E)」）
    s = re.sub(r"\bthe\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


# 人工核对的同名异实：(Seshat 名称归一化键, Wikidata QID) → 理由
EXCLUDE = {("mamluksultanate", "Q847420"): "Seshat 指埃及马木留克苏丹国（1250–1517）；Q847420 是德里的马穆鲁克王朝（1206–1290），不同政权"}
MIN_KEY = 5   # 归一化后少于 5 个字母的名称太短，容易同名异实，不参与匹配


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True)
    rows = [r for r in list(wb["Polities"].iter_rows(values_only=True))[1:] if r[1]]
    groups = collections.defaultdict(list)
    for nga, name, pid, a, b, *_ in rows:
        base = name.split(" - ", 1)[1] if " - " in name else name
        groups[norm(base)].append((name.strip(), int(a), int(b), pid, nga))
    with gzip.open(DATA / "states.json.gz", "rt", encoding="utf-8") as fh:
        states = json.load(fh)
    idx = collections.defaultdict(list)
    for s in states:
        # 只按英文主标签匹配（别名会把「Roman Kingdom」匹配到罗马帝国这类不同实体）
        if s.get("en"):
            idx[norm(s["en"])].append(s)
    out, unmatched = {}, []
    for k, ph in groups.items():
        cands = idx.get(k, [])
        if not k or len(k) < MIN_KEY or not cands:
            unmatched.append(ph[0][0])
            continue
        cands = [c for c in cands if (k, c["id"]) not in EXCLUDE]
        if not cands:
            unmatched.append(ph[0][0] + "（人工排除：同名不同实体）")
            continue
        s = max(cands, key=lambda x: x.get("sl", 0))
        a, b = min(p[1] for p in ph), max(p[2] for p in ph)
        wa = (s.get("from") or {}).get("y")
        wb_ = (s.get("to") or {}).get("y")
        da = None if wa is None else wa - a
        db = None if wb_ is None else wb_ - b
        # 存在期完全不重叠 ⇒ 同名不同实体（如 Seshat「Ghana Empire」与现代加纳），不作比较
        if wa is not None and (wa > b + 50 or (wb_ is not None and wb_ < a - 50)):
            unmatched.append(ph[0][0] + "（同名不同实体）")
            continue
        status = "agree" if (da is not None and abs(da) <= TOL and (db is None or abs(db) <= TOL)) else (
            "conflict" if (da is not None and abs(da) > TOL) or (db is not None and abs(db) > TOL) else "partial")
        out[s["id"]] = {"name": s.get("zh") or s.get("en"), "seshat": [ph[0][0], a, b, sorted({p[3] for p in ph})],
                        "wikidata": [wa, wb_], "diff_start": da, "diff_end": db, "status": status}
    (DATA / "xcheck").mkdir(exist_ok=True)
    (DATA / "xcheck" / "seshat.json").write_text(json.dumps({"source": "Seshat Equinox-2020 (CC BY-NC-SA 4.0)",
                                                            "tolerance_years": TOL, "records": out,
                                                            "unmatched": sorted(unmatched)}, ensure_ascii=False, indent=0),
                                                encoding="utf-8")
    c = collections.Counter(r["status"] for r in out.values())
    print("seshat polity groups:", len(groups), "matched:", len(out), dict(c), "unmatched:", len(unmatched))


if __name__ == "__main__":
    main()
