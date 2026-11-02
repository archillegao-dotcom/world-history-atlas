"""
按日期的国旗：Wikidata P41（国旗）带起止限定（P580/P582）的全部语句 → data/flags.json.gz
  {qid: [{"v": Commons 文件名, "from": t, "to": t, "pref": bool}]}
人工修正 data/curated/flag_overrides.json（如 1928-12-29 起的中华民国国旗「青天白日满地红」，每条注明来源）
优先于 Wikidata。读取 tools/build_states.py 已缓存的 SPARQL 结果（data/cache/raw/st_P41_*.json.gz，取最新）。
"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_states import qual_rows  # noqa: E402
from wdsparql import DATA, write_gz  # noqa: E402

raw = sorted((DATA / "cache" / "raw").glob("st_P41_*.json.gz"), key=lambda p: p.stat().st_mtime)[-1]
rows = json.load(gzip.open(raw))
if isinstance(rows, dict):
    rows = rows.get("results", {}).get("bindings", rows.get("rows", []))
out = {}
for s, lst in qual_rows(rows, "s").items():
    for x in lst:
        x["v"] = x["v"].rsplit("/", 1)[-1] if isinstance(x["v"], str) else x["v"]
    out[s] = lst
ov = json.loads((DATA / "curated" / "flag_overrides.json").read_text(encoding="utf-8"))
pat = ov.get("exclude_patterns", [])
for q in list(out):
    out[q] = [x for x in out[q] if not any(pp in str(x["v"]) for pp in pat)]
    if not out[q]:
        del out[q]
for q, lst in ov["flags"].items():
    out[q] = [{**x, "curated": True} for x in lst]
write_gz(DATA / "flags.json.gz", out)
print(raw.name, len(out), "states;", sum(len(v) for v in out.values()), "flag statements;", sum(1 for v in out.values() if any(x.get("from") or x.get("to") for x in v)), "with dates")
