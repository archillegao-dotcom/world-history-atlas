"""2026-11-22 条约续核。

在第四批仍待核的清单上，核对本批改过的条目，并写出 docs/TREATY_AUDIT_FOLLOWUP.md。
已核对、间隔属实的类型见 data/curated/treaty_verdicts.json，从待核里勾销。
没有来源的不改日期、不改缔约方。
用法：.venv/bin/python tools/accept/treaty_followup_audit.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "accept"))

from backend.datafile import read_json
from backend.modules.treaty_time import apply_succession, leaked_years
from treaty_temporal_audit import apply, issues_for, load_states

DATA = ROOT / "data"
OUT = ROOT / "docs" / "TREATY_AUDIT_FOLLOWUP.md"
BASELINE = 1872
NAMES = {
    "effective_before_signed": "生效早于签署",
    "end_before_effective": "终止早于生效",
    "end_before_signed": "终止早于签署",
    "no_date": "没有可定位的日期",
    "long_gap": "生效比签署晚十五年",
    "future_text": "文本里有晚于生效年的年份",
    "mixed_span": "签署与生效相距远，文本夹着中间的年份",
    "party_unknown": "缔约方不在政权表",
    "party_undated": "缔约方没有起始年",
    "party_not_yet": "签署时该政权尚未开始",
    "party_ended": "签署时该政权已经结束",
    "successor_unmarked": "后来的政权被写成签署方，没有标继承",
    "view_leak": "签署日视图出现更晚的年份",
}


def _issues(raw, fixes, states):
    base = apply(raw, fixes)
    done = json.loads(json.dumps(base))
    apply_succession(done, states)
    return issues_for(done, states, "done")


def main():
    # 公元前的年份不再被当成公元后的更晚年份。反例仍须留下。
    if leaked_years("大部分埃及学家认为它签于公元前1259年。", -1259, {-1259}):
        print("BCE false positive still flagged")
        return 1
    if 1995 not in leaked_years("1995年审议并无限期延长。", 1970, {1970}):
        print("real future year was hidden")
        return 1

    raw = read_json(DATA / "treaties.json.gz", [])
    fixes = json.loads((DATA / "curated" / "treaty_fixes.json").read_text(encoding="utf-8"))
    verdicts = json.loads((DATA / "curated" / "treaty_verdicts.json").read_text(encoding="utf-8"))
    states = load_states()
    before_fixes = {
        k: v for k, v in fixes.items()
        if not (isinstance(v, dict) and v.get("batch") == "2026-11-22")
    }
    before = _issues(raw, before_fixes, states)
    after = _issues(raw, fixes, states)
    cleared_verdict = []
    pending = []
    for tid, typ, detail in after:
        hit = (verdicts.get(tid) or {}).get(typ) or {}
        if hit.get("verdict") == "verified_ok" and hit.get("sources"):
            cleared_verdict.append((tid, typ, detail, hit))
        else:
            pending.append((tid, typ, detail))
    before_keys = {(t, y) for t, y, _ in before}
    after_keys = {(t, y) for t, y, _ in after}
    gone = sorted(before_keys - after_keys)
    added = sorted(after_keys - before_keys)
    by_type = Counter(t for _, t, _ in pending)
    batch = [
        (k, v) for k, v in fixes.items()
        if isinstance(v, dict) and v.get("batch") == "2026-11-22" and not k.startswith("_")
    ]

    lines = [
        "# 条约续核（2026-11-22）",
        "",
        "欧洲/巴黎。承接 `docs/TREATY_AUDIT_REPORT.md` 里改显示以后仍待核的 1872 条。",
        "比较规则没有放宽。公元前紧挨在年份前面时，不再把这个四位数当成公元后的更晚年份。正文里没有「前」、又晚于生效年的年份仍然算。",
        "",
        f"本批改数据之前，按现在的比较再数：{len(before)} 条。第四批留下的数字是 {BASELINE}。差出来的 1 条是公元前年份的误报，数据没有改。",
        f"本批写入修正以后，脚本仍标出 {len(after)} 条。其中 {len(cleared_verdict)} 条对过联合国条约集，确认间隔属实，移出待核。",
        f"还待核：{len(pending)} 条。",
        "",
        "没有打开保存机关名册的，不补缔约方，不补月日。",
        "",
        "## 本批改了的条目",
        "",
        "| 条约 | 做了什么 | 来源 |",
        "| --- | --- | --- |",
    ]
    for tid, fx in batch:
        what = (fx.get("note") or fx.get("summary_zh") or "")[:80].replace("\n", " ")
        src = "；".join(fx.get("sources") or [])
        lines.append(f"| `{tid}` | {what} | {src} |")
    lines += [
        "",
        "## 已核对，不是错误",
        "",
    ]
    if cleared_verdict:
        for tid, typ, detail, hit in cleared_verdict:
            lines.append(f"- `{tid}` {NAMES.get(typ, typ)}：{hit.get('note')} {hit['sources'][0]}")
    else:
        lines.append("无。")
    lines += [
        "",
        "## 仍待核",
        "",
        "| 类型 | 条数 |",
        "| --- | ---: |",
    ]
    for key, title in NAMES.items():
        if by_type.get(key):
            lines.append(f"| {title} | {by_type[key]} |")
    lines += [
        "",
        f"相对本批改数据之前，问题键减少 {len(gone)} 个，新增 {len(added)} 个。",
        "",
        "没有改的大块仍是：没有可定位日期的条目不凭标题回填；继承不唯一的不写「后来由某国继承」；波兰 1385 年以后同时有王国和王冠领地两条，1401、1432、1499 年的联合文书不猜其中一条；库班人民共和国终于 1920 年 3 月，而 Q49546374 没有名称，1920 年 8 月 7 日不猜后继。",
        "",
        "生效比签署晚十五年以上、又没有打开保存机关登记册的，包括几份双边投资条约和两份欧洲委员会公约，仍待核。君士坦丁堡公约导出里的生效日是 1988-10-29，摘要写的签署日是 1888-10-29，像是差了一百年，本批没有打开约文，不改。",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"before {len(before)} after {len(after)} verdict {len(cleared_verdict)} pending {len(pending)} gone {len(gone)} added {len(added)}")
    print(dict(by_type))
    if added:
        print("ADDED", added[:20])
    # 本批点名要消失的错误不能还在。
    bad = []
    pending_keys = {(t, y) for t, y, _ in pending}
    for key in (
        ("Q1963613", "effective_before_signed"),
        ("Q8034909", "effective_before_signed"),
        ("Q135010681", "effective_before_signed"),
        ("Q610272", "long_gap"),
        ("Q112183", "party_ended"),
        ("Q233688", "party_ended"),
        ("Q2657887", "party_ended"),
        ("Q3823095", "party_ended"),
        ("Q253155", "view_leak"),
        ("Q686455", "view_leak"),
        ("Q1248976", "long_gap"),
    ):
        if key in pending_keys:
            bad.append(key)
    if bad:
        print("STILL PENDING", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
