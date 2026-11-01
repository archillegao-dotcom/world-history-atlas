"""
官方历任名单（tools/build_official_offices.py → data/official_offices.json.gz）并入 Wikidata 职位。

规则（不推测）：
- 官方名单中的人能对应到该职位已有的 Wikidata 任职者（名称相同，且年份相近）：
  · Wikidata 已有任期 → 保留 Wikidata 值，只记录核对结果（相差超过 1 年记为不一致）；
  · Wikidata 缺任期 → 补上官方任期，标注来源网址。
- 对应不到的人：只在来源精确到日、且不是「仅核对」(check_only) 的名单中新增一条任职记录，
  人物名称取官方名单（人物 ID 形如 "official:立法院院长:韓國瑜"），标注来源网址。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import datafile
from .timeutil import rec_key


# 繁体 / 日本新旧字体 → 简体（仅用于人名比对，不改变显示）
_VAR = str.maketrans(
    "曽衞衛權渕細護煕蔣國韓濱澤邊齋實戶廣鳩恵榮龍經黃嚴陳馬賴蕭張劉謝連蘇貞遊樹鐘輝東臺灣萬長義鄭吳楊許葉趙錢孫學會選內閣竹蔵沢辺斎実戸広栄竜経黄厳陳郎麿",
    "曾卫卫权渊细护熙蒋国韩滨泽边斋实户广鸠惠荣龙经黄严陈马赖萧张刘谢连苏贞游树钟辉东台湾万长义郑吴杨许叶赵钱孙学会选内阁竹藏泽边斋实户广荣龙经黄严陈郎麿")


def _norm(s):
    return re.sub(r"[\s·・．.\-]", "", (s or "")).translate(_VAR).lower()


_HON = re.compile(r"^(the\s+)?(rt\.?\s+hon\.?\s+|right honourable\s+)?(sir\s+|lord\s+|dame\s+)?", re.I)


def _clean_en(s):
    """英文官方名单中的称谓、爵位、勋衔去掉，只留人名（如 'The Rt Hon Sir Keir Starmer KCB KC MP' → 'Keir Starmer'）。"""
    import html
    s = html.unescape(s or "")
    s = re.sub(r"['\"‘’“”].*?['\"‘’“”]", "", s)              # 'The Younger'
    s = re.split(r",|\s\d+(st|nd|rd|th)\s", s)[0]           # ', the Earl of …' / ' 2nd Baronet'
    s = _HON.sub("", s.strip())
    s = re.sub(r"(\s+(KG|KT|KCB|GCB|OM|KC|QC|MP|FRS|CH|PC|OBE|CBE))+$", "", s)
    return s.strip()


def _covered(o, r):
    """该官方任期是否已被 Wikidata 中某位任职者的任期覆盖（多于一半时间）。"""
    a, b = rec_key(r["from"]), rec_key(r.get("to")) if r.get("to") else rec_key(r["from"]) + 0.01
    for h in o.get("holders", []):
        if not h.get("from") or str(h.get("p", "")).startswith("official:"):
            continue
        ha, hb = rec_key(h["from"]), rec_key(h["to"]) if h.get("to") else 2100.0
        if min(b, hb) - max(a, ha) > 0.5 * max(b - a, 0.01):
            return True
    return False


def merge(R, data_dir: Path) -> dict:
    p = data_dir / "official_offices.json.gz"
    if not datafile.exists(p):  # .json.gz（源码）或 .json.xz（打包版）
        return {}
    src = datafile.read_json(p, {})
    by_id = {o["id"]: o for o in R.offices}
    stats = {}
    for key, rec in src.items():
        oid = key.split("#")[0]
        o = by_id.get(oid)
        if o is None:
            o = {"id": oid, "sl": 0, "juris": [rec["state"]], "holders": [], "zh": rec["office_zh"], "official_only": True}
            R.offices.append(o)
            R.office_by_state.setdefault(rec["state"], []).append(o)
            by_id[oid] = o
        before = {"holders": len(o.get("holders", [])), "dated": sum(1 for h in o.get("holders", []) if h.get("from"))}
        names = {}
        for h in o.get("holders", []):
            pr = R.persons.get(h["p"], {})
            for n in (pr.get("zh"), pr.get("en")):
                if n:
                    names.setdefault(_norm(n), []).append(h)
        st = {"official": len(rec["holders"]), "matched": 0, "filled": 0, "added": 0, "agree": 0, "conflict": [], "unmatched": []}
        for r in rec["holders"]:
            en = _clean_en(r.get("name_en") or (r.get("name") if re.match(r"^[A-Za-z]", r.get("name") or "") else ""))
            keys = [_norm(r.get("name_zh")), _norm(r.get("name")), _norm(r.get("name_en")), _norm(en)]
            _fy = (r.get("from") or {}).get("y")
            hs = [h for h in o.get("holders", []) if r.get("qid") and h.get("p") == r["qid"]
                  and (not h.get("from") or _fy is None or abs(h["from"]["y"] - _fy) <= 1)] or None
            if hs is None:
                hs = next((names[k] for k in keys if k and k in names), None)
            fy = r.get("from", {}).get("y") if r.get("from") else None
            if hs is None and en:   # 英文名：按姓氏，且任期年份必须吻合（否则不算对上，避免张冠李戴）
                sur = _norm(en.split()[-1])
                hs = [h for k, lst in names.items() if sur and sur in k for h in lst
                      if h.get("from") and fy is not None and h["from"]["y"] - 1 <= fy <= (h.get("to") or {"y": 9999})["y"] + 1] or None
            if hs:
                h = min(hs, key=lambda h: abs((h.get("from") or {"y": 9999})["y"] - (fy or 0)))
                if h.get("from") and fy is not None and abs(h["from"]["y"] - fy) > 1:
                    hs2 = [x for x in hs if not x.get("from")]
                    h = hs2[0] if hs2 else h
                st["matched"] += 1
                if h.get("from"):
                    ty = (h.get("to") or {"y": 9999})["y"]
                    if fy is None or abs(h["from"]["y"] - fy) <= 1 or h["from"]["y"] - 1 <= fy <= ty + 1:
                        st["agree"] += 1
                    else:
                        st["conflict"].append([r["name"], h["from"]["y"], fy])
                elif r.get("from"):
                    h["from"] = r["from"]
                    if r.get("to") and not h.get("to"):
                        h["to"] = r["to"]
                    h["src"] = r["src"]
                    st["filled"] += 1
            elif not r.get("check_only") and r.get("from") and r["from"].get("d") and _covered(o, r):
                st["unmatched"].append(r["name"] + "（该时段已有 Wikidata 任职者，未新增）")
            elif not r.get("check_only") and r.get("from") and r["from"].get("d"):
                pid = r.get("qid") or f"official:{rec['office_zh']}:{r['name']}"
                R.persons.setdefault(pid, {"id": pid, "zh": r.get("name_zh") or r["name"], "en": r.get("name_en"),
                                           "desc": f"据{'官方名单：' if rec.get('kind') != 'wikidata' else ''}{rec['source_name']}"})
                o.setdefault("holders", []).append({"p": pid, "from": r["from"], "to": r.get("to"), "src": r["src"]})
                st["added"] += 1
            else:
                st["unmatched"].append(r["name"])
        o.setdefault("sources", []).append({"name": rec["source_name"], "url": rec["source_url"]})
        after = {"holders": len(o.get("holders", [])), "dated": sum(1 for h in o.get("holders", []) if h.get("from"))}
        stats[key] = {"office": rec["office_zh"], "before": before, "after": after, **st}
    return stats
