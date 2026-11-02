"""v0.6.1：逐条核对 data/audit/leader_gaps.md 的君主任职空档（logs/interregna.json 的 gaps）。
第 1 步（离线，按面板实际逻辑）：在空档内逐月取样，看面板会不会显示君主——
  同一政权任何君主类职位的任职者（含只精确到年的记录，按 leaders._holding 的规则）、
  国家元首（P35）、或 interregna.json 个案。全部月份都有人 → 类别 c（扫描只看单一职位、只计精确到月的记录造成的假象）。
  空档超出该政权存续期的部分不计（职位被多个政权共用造成的假象，同属 c）。
结果 → logs/gap_verify_step1.json"""
import json, re, sys, collections
sys.path.insert(0, ".")
from backend import config
from backend.polity import PolityResolver, lifespan
from backend.timeutil import HDate, rec_key
from backend.interregna import _cases, valid_at as iv
from backend.modules.leaders import _holding
MON = re.compile(r"(?i)\b(king|queen regnant|queen|emperor|empress|sultan|tsar|czar|shah|caliph|pharaoh|monarch|khagan|khan|rulers?|duke|prince|grand duke|doge|emir|regent|head of state)\b")
MON_X = re.compile(r"(?i)consort|crown|heir|viceroy|titular|pretender|claimant|anti-|dowager|mother|spouse|wife")
R = PolityResolver(config.DATA_DIR)
cases = _cases(config.DATA_DIR)
gaps = json.load(open("logs/interregna.json"))["gaps"]
def months(a, b):
    out = []; t = a + 1 / 24
    while t < b:
        yy = int(t // 1); mm = min(12, int((t - yy) * 12) + 1)
        if yy != 0:
            out.append(HDate(yy, mm, 15))
        t += 1 / 12
    return out
def who(q, d):
    st = R.states[q]; dk = d.key(); names = []
    for h in _holding([{"from": x.get("from"), "to": x.get("to"), "p": x["v"]} for x in st.get("hos", [])], dk):
        names.append(("hos", h["p"]))
    for o in R.office_by_state.get(q, []):
        en = o.get("en") or ""
        if not (MON.search(en) or o.get("virtual")) or MON_X.search(en):
            continue
        for h in _holding(o.get("holders", []), dk):
            names.append((o["id"], h["p"]))
    for c in cases:
        if q in c["states"] and iv(dk, c["from"], c["to"]):
            names.append(("case", c["id"]))
    return names
out = []
for g in gaps:
    q = g["state"]; st = R.states.get(q)
    a, b, _ = lifespan(st)
    ka = rec_key(a) if a else -1e9; kb = rec_key(b) if b else 1e9
    lo, hi = max(g["from"], ka), min(g["to"], kb)
    ms = months(lo, hi) if hi > lo else []
    empty = [d for d in ms if not who(q, d)]
    spans = []
    for d in empty:
        k = d.y + (d.m - 1) / 12
        if spans and k - spans[-1][1] <= 1 / 12 + 1e-6:
            spans[-1][1] = k
        else:
            spans.append([k, k])
    cls = None
    if hi <= lo:
        cls = ["c", "空档在该政权存续期以外（同一职位被前后多个政权共用）"]
    elif not empty:
        cls = ["c", "面板在整个空档内都显示君主（由其他君主类职位、国家元首或只精确到年的任职记录覆盖；扫描只看单一职位且只计精确到月的记录）"]
    out.append({**g, "lifespan": [ka, kb], "months": len(ms), "empty_months": len(empty),
                "empty_spans": [[round(x, 2), round(y + 1 / 12, 2)] for x, y in spans], "cls": cls})
json.dump(out, open("logs/gap_verify_step1.json", "w"), ensure_ascii=False, indent=0)
print("total", len(out), "covered-by-cases", sum(1 for g in out if g["covered"]))
print(collections.Counter(g["cls"][1][:12] if g["cls"] else "OPEN" for g in out))
rem = [g for g in out if not g["cls"]]
print("remaining", len(rem), "empty months", sum(g["empty_months"] for g in rem))
for g in sorted(rem, key=lambda g: -g["empty_months"]):
    print(g["state"], g["state_zh"], "|", g["office"], g["from"], g["to"], "empty", g["empty_months"], g["empty_spans"][:4], "next", g["next"], g["covered"])
