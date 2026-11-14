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
from backend.modules.treaty_time import (
    apply_succession, clip_text, leaked_years, own_years as own_years_new,
)

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


def issues_for(recs, states, mode="old"):
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
        owned = own_years(r)
        if mode == "old":
            years = [int(y) for y in YEAR.findall(text_of(r))]
            if ey:
                late = sorted({y for y in years if y > ey and y not in owned})
                if late:
                    out.append((tid, "future_text", "摘要或名称里有晚于生效年的年份 " + ",".join(map(str, late[:6]))))
                if sy and ey - sy > 15:
                    mid = sorted({y for y in years if sy < y < ey})
                    if mid:
                        out.append((tid, "mixed_span", "签署与生效之间的年份 " + ",".join(map(str, mid[:6]))))
        elif ey:
            late = _body_years(r, ey, mode)
            if late:
                out.append((tid, "future_text", "摘要或名称里有晚于生效年的年份 " + ",".join(map(str, late[:6]))))
            if sy and ey - sy > 15:
                raw = text_of(r)
                mid = sorted({y for y in leaked_years(raw, sy, owned) if y < ey})
                if mid:
                    out.append((tid, "mixed_span", "签署与生效之间的年份 " + ",".join(map(str, mid[:6]))))
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
        leak = view_leak(r, mode)
        if leak:
            out.append((tid, "view_leak", leak))
    return out


def _body_bits(r, cap, mode):
    """名称始终原样。摘要和短注只在 done 时按年份裁掉回顾句。"""
    date = f"{cap:04d}-12-31" if mode == "done" else None
    bits = [r.get("zh") or "", r.get("en") or ""]
    for bit in (r.get("desc") or "",):
        bits.append(clip_text(bit, date, r) if date else bit)
    sm = r.get("summary")
    text = sm.get("text") if isinstance(sm, dict) else ""
    bits.append(clip_text(text, date, r) if date else (text or ""))
    return "\n".join(bits)


def _body_years(r, cap, mode):
    owned = own_years_new(r)
    if mode == "done":
        return leaked_years(_body_bits(r, cap, mode), cap, owned)
    return leaked_years(text_of(r), cap, owned)


def view_leak(r, mode="old"):
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
    cap = signed["y"]
    if r.get("effective") and r["effective"].get("y"):
        cap = max(cap, r["effective"]["y"])
    if r.get("intended_effective") and r["intended_effective"].get("y"):
        cap = max(cap, r["intended_effective"]["y"])
    if mode == "old":
        bits = [r.get("desc") or "", r.get("fix_note") or ""]
        sm = r.get("summary")
        if isinstance(sm, dict):
            bits.append(sm.get("text") or "")
        if not view.get("hide_end"):
            bits.append(json.dumps(r.get("end"), ensure_ascii=False))
        late = sorted({int(y) for y in YEAR.findall("\n".join(bits)) if int(y) > cap})
    else:
        bits = []
        date_cap = f"{cap:04d}-12-31" if mode == "done" else None
        for bit in (r.get("desc") or "", r.get("fix_note") or ""):
            bits.append(clip_text(bit, date_cap, r) if date_cap else bit)
        sm = r.get("summary")
        text = sm.get("text") if isinstance(sm, dict) else ""
        bits.append(clip_text(text, date_cap, r) if date_cap else (text or ""))
        if not view.get("hide_end"):
            bits.append(json.dumps(r.get("end"), ensure_ascii=False))
        late = leaked_years("\n".join(bits), cap, own_years_new(r))
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


def _name(states, sid):
    st = states.get(sid) or {}
    return st.get("zh") or st.get("en") or sid


def main():
    raw = read_json(DATA / "treaties.json.gz", [])
    fixes = json.loads((DATA / "curated" / "treaty_fixes.json").read_text(encoding="utf-8"))
    states = load_states()
    base = apply(raw, fixes)
    old = issues_for(base, states, "old")
    rules = issues_for(base, states, "rules")
    done_recs = json.loads(json.dumps(base))
    n_rewrite = apply_succession(done_recs, states)
    done = issues_for(done_recs, states, "done")
    old_c = Counter(t for _, t, _ in old)
    rules_c = Counter(t for _, t, _ in rules)
    done_c = Counter(t for _, t, _ in done)
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
        "2026-11-14（欧洲/巴黎）。脚本 `tools/accept/treaty_temporal_audit.py`。第四批处理第三批留下的待核。这不是全库已经改完。",
        "",
        "比较仍用同一套日期规则：只在年份或月日已经能分出先后时才算颠倒。缺月日的同年不算颠倒。政权起讫用 `data/states.json` 里已有的起止，不另推建国日。",
        "",
        f"第四批开始时（第三批拆开海上人命安全公约之后）：{len(old)} 条。",
        f"判定收紧以后、还没改显示：{len(rules)} 条。差出来的是误报，不是把检查放宽。",
        f"改了显示以后仍待核：{len(done)} 条。单一继承改写了 {n_rewrite} 个缔约方。",
        "",
        "## 分桶",
        "",
        "误报是判定改了、数据没改。已改显示是视图或缔约方名称改了。仍待核是两步之后还在。",
        "",
        "| 类型 | 修前 | 误报 | 已改显示 | 仍待核 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key in names:
        a, b, c = old_c.get(key, 0), rules_c.get(key, 0), done_c.get(key, 0)
        lines.append(f"| {names[key]} | {a} | {a - b} | {b - c} | {c} |")
    lines += [
        "",
        "## 误报：判定收紧，检查没有放宽",
        "",
        "三条约定。每条都留着反例，避免为了把数字做小而放过真泄露。",
        "",
        "1. 斜线或拉丁字母后面的四位数是文书编号，不是年份。例：`Q63413419` 的摘要写「第CETS/2002号」。2002 紧跟在斜线后面，是编号残片（修订后的欧洲收养儿童公约在欧洲委员会系列里是 CETS 第 202 号，这条机器翻译把编号写乱了）。不把 2002 当成日历年，也不另编一个正确编号。`1856阿根廷-智利条约` 这种标题里的年份仍然算年份：它没有斜线，结构化日期对不上时继续待核。",
        "",
        "2. 名称或短注里的起讫，左端就是这一条自己的年份时，右端不是另一份后来的条约。例：`Q167759`《波罗的海公约》的短注写「1934-1940」。1934 是签订年，1940 是这个名称自带的结束年。叙述句里另写「1940年被占领」这类事后句子，不吃这条豁免，仍会按下面的规则隐藏。",
        "",
        "3. 条约自己写下的期限留在签署日。例：`Q622649`《单一欧洲法案》写「于1992年12月31日前建立单一市场」。法案 1986 年 2 月签署、1987-07-01 生效，1992 这个日子是法案里的目标，不是后来才发生的事。欧洲联盟官方文本：<https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:11986U/TXT>。同一句如果又写「截至」「改为」「延长」，整句仍隐藏，不把回顾句当成期限。",
        "",
        "## 已改显示",
        "",
        "### 以后的年份",
        "",
        "摘要和短注按句切开。一句里有晚于所选年份的数字时，默认整句等到那个年份才出现。贴着「签署」「生效」「通过」「签订」「订于」的年份留下，仍算待核，因为那可能是这条自己的日期和字段不一致。上面说的期限留下，不算错误。同一句如果又写截至、改为、延长这类回顾，整句仍等到最晚的年份。一句里有两个更晚的年份时，整句等到最晚的那个年份。按年份，不按月日。名称不删。",
        "",
        "抽了五句，对过公开文本：",
        "",
        "1. `Q186444`《不扩散核武器条约》生效年是 1970。摘要写 1995 年 5 月缔约方开会并无限期延长。这是 1995 年审议和延期大会的决定，不是 1970 年的约文。1970 年的视图不放这句，1995 年起放。联合国裁军页面记这次延期：<https://disarmament.unoda.org/wmd/nuclear/npt/>。",
        "2. `Q171328`《联合国宪章》1945-10-24 生效。摘要写 1946 年 1 月大会第一届会议在伦敦开。1945 年的视图不放这句。",
        "3. `Q167457`《罗马条约》1958 年生效。摘要把 1993 年马斯特里赫特条约的改名和 2009 年里斯本条约写在同一句。1993 年还没到 2009，整句仍不出现；2009 年起出现。",
        "4. `Q191836`《濒危野生动植物种国际贸易公约》1975 年生效。摘要「截至2025年11月，共有185个缔约方」是后来的统计，2025 年以前不放。",
        "5. `Q170170`《湿地公约》1975 年生效。摘要「直至2014年1月……168个缔约成员」是后来的统计，2014 年以前不放。",
        "",
        "贴着签署或生效、又没有回顾用语的句子不隐藏，仍留在待核里。",
        "",
        "### 单一继承",
        "",
        "只在下面几条同时成立时，把缔约方改成当时的政权，并写「后来由 X 继承」。X 是原来写在这条上的后来政权，不是新找的国家。",
        "",
        "- 条约有签署、通过或生效日，而且这个日子确实早于该政权在表里的起始。",
        "- `replaces` 里当时还在的前身只有一个，而且这个前身有终止年。另一个没有终止年、日子又落在它起始之后的对象（例如日本条目上的第二尚氏）会使前身不唯一，整条不改。",
        "- 这个前身的 `replaced_by` 里只有这一个政权。英国同时指向爱尔兰自由邦，德意志国同时指向民主德国和联邦德国，这种不写「后来由英国继承」或「后来由德国继承」。",
        "- 前身的终止年和后继的起始年相差不超过两年，也不提前超过一年。梵蒂冈和教皇国隔了几十年，西班牙和阿拉贡隔了几个世纪，都不改。",
        "- 两边都有坐标时，距离不超过 800 公里。",
        "- 前身名称是殖民地、自治领、保护国、西南非、罗得西亚、黄金海岸、教长国、停战诸国、苏维埃或社会主义共和国、苏丹国的，不改。锡金邦这种以「邦」结尾的也不改。",
        "- 缔约方超过 15 个的不改。防止船舶污染公约 163 方、世界版权公约 96 方，名单是后来的成员国，没有各国加入日。把纳米比亚改成西南非，等于写成 1983 年西南非签了字。",
        "- 标题是「国际公约」但名单不足 8 国的不改。那是摘录不全，不是一份只有几国的条约。",
        "- 没有中文名也没有英文名的条目不改。",
        "",
        "这一步只改已经写在名单里的那一方。当时的政权不在名单里时，把后来的国名改成当时的政权。当时的政权已经在名单里时，去掉重复的后来国名，并在当时政权上写继承。不另找签署方。名单本身多写或少写的，改名不能把它变成对的，那种仍待核。",
        "",
        "打开过原文的五条：",
        "",
        "1. `Q193270`《拉特兰条约》，1929-02-11。原文写 Vittorio Emanuele III Re d'Italia，不是 1946 年的意大利共和国。显示意大利王国，注明后来由意大利继承。<https://www.vatican.va/roman_curia/secretariat_state/archivio/documents/rc_seg-st_19290211_patti-lateranensi_it.html>",
        "2. `Q193258`《洛桑条约》，1923-07-24。土耳其外交部公布的序言写 Serb-Croat-Slovene State。王国改名是政权表里的 1929-10-03。显示塞尔维亚、克罗地亚和斯洛文尼亚王国，注明后来由南斯拉夫王国继承。<https://www.mfa.gov.tr/lausanne-peace-treaty----preamble.en.mfa>",
        "3. `Q698686`《胡贝图斯堡条约》，1763-02-15。美因茨欧洲史研究所刊出的约文写 Roi de Pologne Electeur de Saxe。萨克森王国是 1806 年。显示萨克森选帝侯，注明后来由萨克森王国继承。<https://www.ieg-friedensvertraege.de/---_site.popup..html_dir._treaty.3_comment.93_notrans.1_likecms.html>",
        "4. `Q1160895`《1839年伦敦条约》，1839-04-19。约文写 His Majesty the King of the French，这是七月王朝的称号。法兰西第二共和国是 1848 年。显示七月王朝，注明后来由法兰西第二共和国继承。<https://firstworldwar.com/source/london1839.htm>",
        "5. `Q183080`《保护工业产权巴黎公约》，1883-03-20。英国条约集把意大利列在当日的签署国里。当时是意大利王国。显示意大利王国，注明后来由意大利继承。<https://mansfield.bailii.org/uk/other/UKTS/1883/TS0034.html>",
        "",
        "同一条规则还盖到伯尔尼公约上的意大利、1913 年伦敦条约上的意大利、1894 年霍乱公约上的意大利、1925 年英意照会、宁芬堡条约上的萨克森、华沙条约上的罗马尼亚人民共和国、1979 年南部非洲互不侵犯条约和 1988 年两条安哥拉协定、1965 年德国—伊朗和德国—塞拉利昂双边投资条约。这些没有逐份再打开原文。规则对不上的没有用这条去套。",
        "",
        "故意没有改的近例：",
        "",
        "- `Q1342523`《日英和亲条约》（1854）不写成第二尚氏。日本的替换列表里还有没有终止年的琉球王统，前身不唯一。",
        "- `Q651219` 防止船舶污染国际公约不把纳米比亚写成西南非。163 个缔约方，没有加入日。",
        "- `Q111644445`《哈默顿条约》（1845）不写成阿曼教长国。条约是马斯喀特苏丹和英国的照会，教长国是另一个政权。",
        "- `Q7837260` 蒂塔利亚条约不把锡金王国改挂到锡金邦下面再写继承。锡金邦是后来的一级行政区。",
        "",
        "改写了的缔约方：",
        "",
    ]
    rewritten = []
    for r in done_recs:
        for p in r.get("parties") or []:
            if p.get("note"):
                rewritten.append((r.get("id"), (r.get("zh") or r.get("en") or "")[:40], _name(states, p["s"]), p["note"]))
    lines.append(f"{len(rewritten)} 处。")
    lines.append("")
    if rewritten:
        lines.append("| 条约 | 名称 | 显示为 | 标注 |")
        lines.append("| --- | --- | --- | --- |")
        for tid, title, shown, note in rewritten:
            lines.append(f"| `{tid}` | {title} | {shown} | {note} |")
        lines.append("")
    lines += [
        "## 仍待核，以及为什么不改",
        "",
        f"还剩 {len(done)} 条。下面按类型说明。没有可靠来源、又不能从政权表里唯一读出来的，不补日期，不补国家。",
        "",
        "- 没有可定位的日期：维基数据没有签署、通过、生效或开始。不能凭标题里的年份回填。",
        "- 缔约方没有起始年：政权表没有 `from`。不知道它在签署日是否已经存在。",
        "- 签署时该政权尚未开始，又没有唯一的当时前身：英国在 1801 年以前只替换大不列颠及爱尔兰联合王国，而那个王国自己还没开始，再往前是两个政权，不选。俄罗斯在表里从 1263 年写起，苏联时期的条约不会进这一桶，本批不改政权表的起始年。塞尔维亚只替换塞尔维亚和黑山；更早的条约日那个国家还不在，不跳过南斯拉夫去改。",
        "- 后来的政权被写成签署方，但继承不是单方：大不列颠及爱尔兰联合王国的后继里还有爱尔兰自由邦；德意志国的后继里还有民主德国。中华人民共和国的前身中华民国，后继列表里不只有中华人民共和国。代表权不是这一句「后来由 X 继承」能写成的，本批不标。",
        "- 签署时该政权已经结束：九条。不猜该换成哪一个后继。",
        "- 生效早于签署：三条。生效日可以早于某一国后来的签署，这里的「签署」未必是公约开放签署的那一天。没有打开保存机关的登记册以前不调换。",
        "- 生效比签署晚十五年：这是提示，不是已经证实的错误。《关于国家在条约方面的继承的维也纳公约》1978-08-23 通过、1996-11-06 生效，间隔是批准过程。日内瓦第一公约把 1864 年的签署和 1950-10-21 的生效写在一条，1950-10-21 与 1949 年日内瓦公约的生效日相同，像是两版写进了一条；按版本拆开要另做，本批不拆。双边投资条约的长间隔也不逐份改日期。",
        "- 文本里仍有更晚年份：名称里的年份不删；没有回顾标记、又像是这一条自己的日期的句子不隐藏。",
        "",
        "## 待核样例",
        "",
    ]
    grouped = {}
    for row in done:
        grouped.setdefault(row[1], []).append(row)
    for key, title in names.items():
        rows = grouped.get(key) or []
        if not rows:
            continue
        lines += block(title, rows)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"old {len(old)} rules {len(rules)} done {len(done)} rewrite {n_rewrite}")
    print("old", dict(old_c))
    print("rules", dict(rules_c))
    print("done", dict(done_c))
    bad = [row for row in done if str(row[0]).startswith("curated:solas")]
    print("solas_remaining", bad)
    if len(old) != 2196:
        print("UNEXPECTED old count", len(old))
        bad.append("old-count")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
