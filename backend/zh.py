"""中文名补译（任务 C，v0.6.1）：data/curated/zh_labels.json（QID → 中文名，来自 Wikidata 中文标签或中文维基条目名，tools/zh_fill.py 生成）
与 zh_basemap_names.json（底图名称 → 中文维基链接名）。找不到中文名的，显示原名并标「（暂无通用译名）」。"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

CJK = re.compile(r"[\u4e00-\u9fff]")
NOTR = "（暂无通用译名）"
# 仅供 tools/accept/zh_coverage.py 统计「补译之前」：WHA_ZH_RAW=1 时不补译、不标注
RAW = os.environ.get("WHA_ZH_RAW") == "1"


@lru_cache(maxsize=2)
def labels(data_dir: Path) -> dict:
    if RAW:
        return {}
    out = {}
    for fn in ("zh_labels.json", "zh_manual.json"):   # 人工补译优先
        p = Path(data_dir) / "curated" / fn
        if p.exists():
            out.update({k: v["zh"] for k, v in json.loads(p.read_text(encoding="utf-8"))["labels"].items() if v and v.get("zh")})
    return out


@lru_cache(maxsize=2)
def overrides(data_dir: Path) -> dict:
    """zh_manual.json 中带 override 的条目：已有中文名但有歧义的，也替换。"""
    p = Path(data_dir) / "curated" / "zh_manual.json"
    if RAW or not p.exists():
        return {}
    return {k: v["zh"] for k, v in json.loads(p.read_text(encoding="utf-8"))["labels"].items() if v.get("override")}


@lru_cache(maxsize=2)
def basemap_names(data_dir: Path) -> dict:
    if RAW:
        return {}
    p = Path(data_dir) / "curated" / "zh_basemap_names.json"
    if not p.exists():
        return {}
    return {k: v["zh"] for k, v in json.loads(p.read_text(encoding="utf-8"))["names"].items() if v and v.get("zh")}


def has_zh(s) -> bool:
    return bool(s) and bool(CJK.search(str(s)))


MT = ("（译名）", "（机器翻译）")
LATIN = re.compile(r"[A-Za-z]")


@lru_cache(maxsize=2)
def orig_labels(data_dir: Path) -> dict:
    """没有中文也没有英文标签的人物：Wikidata 任一语言的标签（tools/orig_labels.py）。"""
    p = Path(data_dir) / "curated" / "orig_labels.json"
    if RAW or not p.exists():
        return {}
    return {k: v["label"] for k, v in json.loads(p.read_text(encoding="utf-8"))["labels"].items()}


def fill(recs, data_dir, field="zh"):
    """把补译的中文名写进记录；返回填入条数。
    - 没有汉字的：用 zh_labels / zh_manual 的中文名；
    - 离线机器翻译（带「（译名）」）却还夹着拉丁字母的（如「KV14 车次（译名）」「Aversa 数（译名）」）：不可靠，
      有补译就用补译，否则退回原文（由 disp 标「暂无通用译名」），机器翻译保留在 zh_mt_dropped；
    - 连英文名也没有的人物：用 Wikidata 任一语言的标签作原名。"""
    if RAW:
        return 0
    L = labels(data_dir)
    O = orig_labels(data_dir)
    OV = overrides(data_dir)
    n = 0
    en_f = "en" if field == "zh" else "en_name"
    for r in recs:
        if not isinstance(r, dict):
            continue
        if OV.get(r.get("id")) and field == "zh":
            r["zh_orig"] = r.get("zh")
            r["zh"] = OV[r["id"]]
            n += 1
            continue
        v = r.get(field)
        bad_mt = bool(v) and any(m in v for m in MT) and bool(LATIN.search(v))
        if (not has_zh(v) or bad_mt) and L.get(r.get("id")):
            if field != "zh" and v and not r.get(en_f):
                r[en_f] = v
            r[field] = L[r["id"]]
            r["zh_src"] = "补译"
            n += 1
        elif bad_mt and r.get(en_f):
            r["zh_mt_dropped"] = v
            r[field] = r[en_f] if field != "zh" else None
        if field == "zh" and not r.get("zh") and not r.get("en") and O.get(r.get("id")):
            r["en"] = O[r["id"]]
    return n


def disp(name, en=None):
    """显示名：有汉字原样返回；否则原名加「（暂无通用译名）」。"""
    s = name or en
    if RAW or not s or has_zh(s) or str(s).startswith("Q") and str(s)[1:].isdigit():
        return s
    return f"{s}{NOTR}"
