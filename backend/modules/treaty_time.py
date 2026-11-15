"""条约在所选日期上的两处校正。

单一继承：缔约方条目的起始年晚于条约，政权表里又只有一个当时还在、
并且年份和它首尾相接的前身时，显示那个前身，并注明后来由哪一个条目继承。
后继不止一方、前身是殖民地或另一国、名单长得像「现在的成员国」时，不改。

以后的年份：摘要里写事后回顾的句子，要到那个年份才放进视图。
文书编号里的四位数字、名称里自带的起讫、条约自己写下的期限，不当成泄露。
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from ..datafile import read_json

# 斜线或拉丁字母后面的四位数是文书编号（第CETS/2002号），不是年份。
YEAR = re.compile(r"(?<![\d/A-Za-z])((?:1[0-9]{3}|20[0-9]{2}))(?!\d)")
YEAR_OLD = re.compile(r"(?<!\d)((?:1[0-9]{3}|20[0-9]{2}))(?!\d)")
RANGE = re.compile(
    r"(?<![\d/A-Za-z])((?:1[0-9]{3}|20[0-9]{2}))\s*[-–—~～至到]\s*((?:1[0-9]{3}|20[0-9]{2}))(?!\d)"
)
# 期限是条约自己的话。回顾句里的「改为」不能靠这一条留下。
DEADLINE = re.compile(r"日前建立|前建立|不迟于|不晚于|no later than|by 31 December", re.I)
RETRO = re.compile(
    r"截至|直至|直到|为止|已有|共有|延长|到期|改为|改名|签署国包括|年间|后来|加入|会议|as of",
    re.I,
)
# 这些前身不是同一个政权换了宪法名称。
NOT_SAME = re.compile(
    r"殖民地|自治领|保护国|西南非|罗得西亚|黄金海岸|教长|停战诸国|苏维埃|社会主义共和国|苏丹国"
)


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


def anchor(r):
    return r.get("signed") or r.get("adopted") or r.get("effective") or r.get("start") or r.get("inception")


def view_year(date_str):
    if not date_str or len(date_str) < 4 or not date_str[:4].isdigit():
        return None
    return int(date_str[:4])


def load_polities(data_dir):
    data = Path(data_dir)
    states = {s["id"]: s for s in read_json(data / "states.json.gz", []) if isinstance(s, dict) and s.get("id")}
    extra = data / "curated" / "runtime_states.json"
    if extra.exists():
        for q, r in json.loads(extra.read_text(encoding="utf-8")).items():
            if q.startswith("Q") and q not in states and isinstance(r, dict):
                states[q] = {**r, "curated": True}
    overrides = data / "curated" / "lifespan_overrides.json"
    if overrides.exists():
        for q, r in json.loads(overrides.read_text(encoding="utf-8")).items():
            st = states.get(q)
            if not st or q.startswith("_") or not isinstance(r, dict):
                continue
            for k in ("from", "to"):
                if k in r:
                    st[k] = r[k]
    return states


def _covers(st, when) -> bool:
    pa, pb = st.get("from"), st.get("to")
    if not pa or certainly_before(when, pa):
        return False
    if pb and certainly_before(pb, when):
        return False
    return True


def _km(a, b):
    if not a or not b or len(a) < 2 or len(b) < 2:
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, [a[1], a[0], b[1], b[0]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(min(1.0, math.sqrt(h)))


def predecessor_for(st, when, states):
    """当时唯一、年份相接、表格里又只由这一国继承的前身。对不上就返回空。"""
    if not st or not st.get("from") or not certainly_before(when, st["from"]):
        return None
    reps = []
    for rep in st.get("replaces") or []:
        prev = states.get(rep.get("v"))
        if prev:
            reps.append(prev)
    alive = [p for p in reps if _covers(p, when)]
    if len(alive) != 1:
        return None
    prev = alive[0]
    if not prev.get("from") or not prev.get("to"):
        return None
    others = [
        x for x in reps
        if x.get("id") != prev.get("id") and x.get("from")
        and not certainly_before(when, x["from"])
        and not (x.get("to") and certainly_before(x["to"], when))
    ]
    if others:
        return None
    rb = [x.get("v") for x in (prev.get("replaced_by") or []) if states.get(x.get("v"))]
    if rb != [st.get("id")]:
        return None
    gap = st["from"]["y"] - prev["to"]["y"]
    if gap < -1 or gap > 2:
        return None
    dist = _km(st.get("coord"), prev.get("coord"))
    if dist is not None and dist > 800:
        return None
    label = (prev.get("zh") or "") + (prev.get("en") or "")
    if NOT_SAME.search(label):
        return None
    if (st.get("zh") or "").endswith("邦"):
        return None
    return prev


def _treaty_ok(r) -> bool:
    """名单太长，或「国际公约」却只摘了几国，都不改。那是后来的成员国，不是签署日的前身。"""
    if not (r.get("zh") or r.get("en")):
        return False
    parties = r.get("parties") or []
    if not parties or len(parties) > 15:
        return False
    title = (r.get("zh") or "") + (r.get("en") or "")
    if "国际公约" in title and len(parties) < 8:
        return False
    return True


def apply_succession(recs, states) -> int:
    """就地改显示。返回改写的缔约方条数。已经改过的再跑不会再改。"""
    n = 0
    for r in recs:
        if not isinstance(r, dict) or not _treaty_ok(r):
            continue
        when = anchor(r)
        if not when:
            continue
        also = list(r.get("also_show") or [])
        also_ids = {p.get("s") for p in also}
        new, seen, changed = [], set(), False
        for p in r.get("parties") or []:
            sid = p.get("s")
            st = states.get(sid) if sid else None
            prev = predecessor_for(st, when, states) if st else None
            if not prev:
                if not sid or sid not in seen:
                    if sid:
                        seen.add(sid)
                    new.append(p)
                continue
            note = "后来由" + (st.get("zh") or st.get("en") or sid) + "继承"
            changed = True
            n += 1
            if sid not in also_ids:
                also.append({"s": sid, "how": note})
                also_ids.add(sid)
            if prev["id"] in seen:
                for q in new:
                    if q.get("s") == prev["id"] and not q.get("note"):
                        q["note"] = note
                        q["later"] = sid
                continue
            q = dict(p)
            q["s"] = prev["id"]
            q["note"] = note
            q["later"] = sid
            seen.add(prev["id"])
            new.append(q)
        if changed:
            r["parties"] = new
            r["also_show"] = also
    return n


def _range_ends(text, cap, owned):
    """起讫的左端就是这一条自己的年份时，右端不是另一件后来的事。"""
    ends = set()
    for a, b in RANGE.findall(text or ""):
        ia, ib = int(a), int(b)
        if ia in owned or (cap is not None and ia <= cap):
            ends.add(ib)
    return ends


def late_years(text, cap, owned, old=False):
    if cap is None or not text:
        return []
    pat = YEAR_OLD if old else YEAR
    found = {int(y) for y in pat.findall(text)}
    if not old:
        found -= _range_ends(text, cap, owned)
    return sorted(y for y in found if y > cap and y not in owned)


def _near_own_date(part, cap, owned) -> bool:
    """更晚的年份就贴在「签署 / 生效 / 通过」旁边时，先当这一条自己的日期，不藏。"""
    if RETRO.search(part):
        return False
    for y in late_years(part, cap, owned, old=False):
        close = False
        for m in re.finditer(rf"(?<!\d){y}(?!\d)", part):
            window = part[max(0, m.start() - 6):m.end() + 6]
            if re.search(r"签署|生效|通过|签订|订于", window):
                close = True
                break
        if not close:
            return False
    return True


def _keep_sentence(part, cap, owned) -> bool:
    late = late_years(part, cap, owned, old=False)
    if not late:
        return True
    # 期限留下。同一句又在做事后回顾时，整句仍等到最晚的年份。
    if DEADLINE.search(part) and not RETRO.search(part):
        return True
    if _near_own_date(part, cap, owned):
        return True
    return False


def clip_text(text, date_str, rec):
    """回顾句在所选年份还没到时不放进视图。名称不改。"""
    if not text or not date_str:
        return text or ""
    cap = view_year(date_str)
    if cap is None:
        return text
    owned = own_years(rec)
    parts = re.split(r"(?<=[。！？!?；;\n])", text)
    return "".join(p for p in parts if _keep_sentence(p, cap, owned)).strip()


def leaked_years(text, cap, owned, *, clip_date=None, rec=None, old=False):
    """审计用。clip_date 给定时先按视图裁句，再找还露在外面的年份。"""
    if clip_date and rec is not None:
        text = clip_text(text, clip_date, rec)
    if old:
        return late_years(text, cap, owned, old=True)
    # 期限句里的年份不算泄露。起讫和文书编号已经在 late_years 里去掉。
    if not text or cap is None:
        return []
    parts = re.split(r"(?<=[。！？!?；;\n])", text)
    found = set()
    for part in parts:
        if DEADLINE.search(part) and not RETRO.search(part):
            continue
        found.update(late_years(part, cap, owned, old=False))
    return sorted(found)
