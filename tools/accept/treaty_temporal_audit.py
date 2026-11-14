"""全库条约的时间一致性审计。

检查日期顺序、所选日期会不会带出以后的年份、缔约方在签署日是否已经存在。
用法：python3 tools/accept/treaty_temporal_audit.py
写出 docs/TREATY_AUDIT_REPORT.md。不改数据。
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.datafile import read_json
from backend.modules.spirits import apply_treaty_fixes, view_of

DATA = ROOT / "data"
OUT = ROOT / "docs" / "TREATY_AUDIT_REPORT.md"
YEAR = re.compile(r"(?<!\d)((?:1[0-9]{3}|20[0-9]{2}))(?!\d)")
SAMPLES = 8


def certainly_before(a, b) -> bool:
    """a 的已知精度已经整段落在 b 之前。同年而缺月日时不算。"""
    if not a or not b or "y" not in a or "y" not in b:
        return False
    if a["y"] != b["y"]:
        return a["y"] < b["y"]
    am, bm = a.get("m") or 0, b.get("m") or 0
    if not am or not bm or am != bm:
        return bool(am and bm and am < bm)
    ad, bd = a.get("d") or 0, b.get("d") or 0
    return bool(ad and bd and ad < bd)


def y_of(t):
    return t.get("y") if isinstance(t, dict) else None


def own_years(r):
    ys = set()
    for k in ("signed", "adopted", "effective", "intended_effective", "end", "start", "inception"):
        y = y_of(r.get(k))
        if y:
            ys.add(y)
    return ys


def text_of(r):
    parts = [r.get("zh") or "", r.get("en") or "", r.get("desc") or ""]
    sm = r.get("summary")
    if isinstance(sm, dict):
        parts.append(sm.get("text") or "")
    return "\n".join(parts)


def anchor(r):
    return r.get("signed") or r.get("adopted") or r.get("effective") or r.get("start") or r.get("inception")


def issues_for(recs, states):
    out = []
    for r in recs:
        tid = r.get("id")
        signed, eff, end = r.get("signed"), r.get("effective"), r.get("end") or r.get("dissolved")
        if certainly_before(eff, signed):
            out.append((tid, "effective_before_signed", f"{eff} < {signed}"))
        if certainly_before(end, eff):
            out.append((tid, "end_before_effective", f"{end} < {eff}"))
        elif certainly_before(end, signed):
            out.append((tid, "end_before_signed", f"{end} < {signed}"))
        if anchor(r) is None:
            out.append((tid, "no_date", "没有签署、通过、生效或开始日期"))
        sy, ey = y_of(signed), y_of(eff)
        if sy and ey and ey - sy > 15:
            out.append((tid, "long_gap", f"{sy} → {ey}"))
        years = [int(y) for y in YEAR.findall(text_of(r))]
        owned = own_years(r)
        if ey:
            late = sorted({y for y in years if y > ey and y not in owned})
            if late:
                out.append((tid, "future_text", "摘要或名称里有晚于生效年的年份 " + ",".join(map(str, late[:6]))))
            if sy and ey - sy > 15:
                mid = sorted({y for y in years if sy < y < ey})
                if mid:
                    out.append((tid, "mixed_span", "签署和生效之间的年份 " + ",".join(map(str, mid[:6]))))
        when = anchor(r)
        if when:
            for p in r.get("parties") or []:
                sid = p.get("s")
                if not sid:
                    continue
                how = (p.get("how") or "") + (p.get("via") or "")
                if "继承" in how:
                    continue
                st = states.get(sid)
                if not st:
                    out.append((tid, "party_unknown", sid))
                    continue
                # 用条目里写下的起止。1800 年前缺终止年时，地图会临时只显示 50 年，那不是终止日，这里不用。
                a, b = st.get("from"), st.get("to")
                if a is None:
                    out.append((tid, "party_undated", sid))
                    continue
                if certainly_before(when, a):
                    replaced = []
                    for rep in st.get("replaces") or []:
                        prev = states.get(rep.get("v"))
                        if not prev:
                            continue
                        pa, pb = prev.get("from"), prev.get("to")
                        if pa and not certainly_before(when, pa) and not (pb and certainly_before(pb, when)):
                            replaced.append(rep.get("v"))
                    if replaced:
                        out.append((tid, "successor_unmarked", f"{sid} 替换 {replaced[0]}，签署日该国尚未开始"))
                    else:
                        out.append((tid, "party_not_yet", f"{sid} 始于 {a}"))
                elif b and certainly_before(b, when):
                    out.append((tid, "party_ended", f"{sid} 终于 {b}"))
        leak = view_leak(r)
        if leak:
            out.append((tid, "view_leak", leak))
    return out


def view_leak(r):
    """在签署日打开时，除这一版自己的生效年以外，正文不应出现更晚的年份。"""
    signed = r.get("signed") or r.get("adopted")
    if not signed or not signed.get("y"):
        return None
    date = f"{signed['y']:04d}" + (f"-{signed['m']:02d}" if signed.get("m") else "")
    if signed.get("m") and signed.get("d"):
        date += f"-{signed['d']:02d}"
    view = view_of(r, date)
    if view.get("withhold"):
        return None
    bits = [r.get("desc") or "", r.get("fix_note") or ""]
    sm = r.get("summary")
    if isinstance(sm, dict):
        bits.append(sm.get("text") or "")
    if not view.get("hide_end"):
        bits.append(json.dumps(r.get("end"), ensure_ascii=False))
    cap = signed["y"]
    if r.get("effective") and r["effective"].get("y"):
        cap = max(cap, r["effective"]["y"])
    if r.get("intended_effective") and r["intended_effective"].get("y"):
        cap = max(cap, r["intended_effective"]["y"])
    late = sorted({int(y) for y in YEAR.findall("\n".join(bits)) if int(y) > cap})
    if late:
        return "签署日视图出现更晚的年份 " + ",".join(map(str, late[:6]))
    return None


def load_states():
    states = {s["id"]: s for s in read_json(DATA / "states.json.gz", []) if isinstance(s, dict) and s.get("id")}
    extra = DATA / "curated" / "runtime_states.json"
    if extra.exists():
        for q, r in json.loads(extra.read_text(encoding="utf-8")).items():
            if q.startswith("Q") and q not in states and isinstance(r, dict):
                states[q] = {**r, "curated": True}
    overrides = DATA / "curated" / "lifespan_overrides.json"
    if overrides.exists():
        for q, r in json.loads(overrides.read_text(encoding="utf-8")).items():
            st = states.get(q)
            if not st or q.startswith("_") or not isinstance(r, dict):
                continue
            for k in ("from", "to"):
                if k in r:
                    st[k] = r[k]
    return states


def apply(raw, fixes):
    recs = json.loads(json.dumps(raw))
    apply_treaty_fixes(recs, DATA, fixes)
    return recs


def block(title, rows):
    lines = [f"### {title}", "", f"{len(rows)} 条。", ""]
    shown = rows[:SAMPLES]
    if shown:
        lines.append("| 条约 | 说明 |")
        lines.append("| --- | --- |")
        for tid, _typ, detail in shown:
            lines.append(f"| `{tid}` | {detail} |")
        if len(rows) > len(shown):
            lines.append("")
            lines.append(f"其余 {len(rows) - len(shown)} 条不逐条展开。")
    lines.append("")
    return lines


def main():
    raw = read_json(DATA / "treaties.json.gz", [])
    fixes = json.loads((DATA / "curated" / "treaty_fixes.json").read_text(encoding="utf-8"))
    states = load_states()
    before_fixes = {k: v for k, v in fixes.items() if not (isinstance(v, dict) and v.get("batch") == 3)}
    pre = issues_for(apply(raw, before_fixes), states)
    post = issues_for(apply(raw, fixes), states)
    pre_c, post_c = Counter(t for _, t, _ in pre), Counter(t for _, t, _ in post)
    fixed = [row for row in pre if row[0] == "Q523582"]
    names = {
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
    lines = [
        "# 条约时间审计",
        "",
        "2026-11-14（欧洲/巴黎）。脚本 `tools/accept/treaty_temporal_audit.py`。这是问题清单，不是全库已经改完。",
        "",
        "比较用的是同一套日期规则：只在年份或月日已经能分出先后时才算颠倒。缺月日的同年不算颠倒。政权起讫用 `data/states.json` 里已有的起止，不另推建国日。",
        "",
        f"第三批修正之前：{len(pre)} 条。其中混在一条里的海上人命安全公约（Q523582）占 {len(fixed)} 条，这一批已拆开，不再显示。",
        f"修正之后仍待核：{len(post)} 条。这一批没有为这些条改写日期或缔约方。",
        "",
        "## 类型",
        "",
        "| 类型 | 修正前 | 修正后（待核） |",
        "| --- | ---: | ---: |",
    ]
    for key in names:
        lines.append(f"| {names[key]} | {pre_c.get(key, 0)} | {post_c.get(key, 0)} |")
    lines += ["", "## 这一批改掉的", "",
              "Q523582 把 1914-01-20 的签署和 1980-05-25 的生效写在同一条，摘要写成 1974/1978。缔约方里有 1949 年才开始的政权。这一条已隐藏。1914、1929、1948、1960、1974 和两份议定书各自成条，日期和摘要只属于该版。",
              ""]
    lines += ["## 待核样例", ""]
    grouped = {}
    for row in post:
        grouped.setdefault(row[1], []).append(row)
    for key, title in names.items():
        rows = grouped.get(key) or []
        if not rows:
            continue
        lines += block(title, rows)
    lines += [
        "待核的条没有改。长间隔可能是批准本来就慢，也可能是把不同版本写进了一条。文本里的更晚年份多半来自维基摘要，没有逐条核对以前不删。缔约方尚未开始或已经结束的，不把现代国名改成推测的前身。",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"pre {len(pre)} fixed_q {len(fixed)} post {len(post)}")
    print("post", dict(post_c))
    # 本批新记录不应再把自己的生效年报成视图泄漏
    bad = [row for row in post if str(row[0]).startswith("curated:solas")]
    print("solas_remaining", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
