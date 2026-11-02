"""第 4 步：汇总 225 处君主空档的最终判定 → data/audit/gap_resolutions.json，并在 data/audit/leader_gaps.md 末尾写核对结果。
a：补了缺失的君主任职记录（extra_holders 带 gap_fix）；b：新增 interregna.json 个案；c：日期精度/扫描假象（含 v0.6.1 修正的 _holding 截断逻辑）；d：无法核实（未记录）。
用法：先跑 tools/audit/gap_verify.py 的离线复核（logs/gap_verify_step1.json 在修复前已存为 logs/gap_verify_before.json）。"""
import json, sys, collections, re
sys.path.insert(0, ".")
from backend import config
from backend.polity import PolityResolver
from backend.timeutil import HDate
from backend.interregna import _cases, valid_at as iv
from backend.modules.leaders import _holding
before = json.load(open("logs/gap_verify_before.json"))
after = {(g["state"], g["office"], g["from"]): g for g in json.load(open("logs/gap_verify_step1.json"))}
R = PolityResolver(config.DATA_DIR)
newcases = {c["id"]: c for c in _cases(config.DATA_DIR)}
import importlib.util
src = open("tools/curated_src/interregna_gaps.py", encoding="utf-8").read()
gapcase_ids = set(re.findall(r'V\("([a-z0-9_]+)"', src)) | {f"poland_{x}" for x in ("1572", "1574", "1632", "1648", "1668", "1673", "1696", "1733", "1763", "1444", "1492", "1501", "1506")}
xo = json.load(open("data/curated/extra_offices.json"))
fix = [h for h in xo["extra_holders"] if h.get("gap_fix")]
M = {  # 修复后仍有空月份的空档：(state, 空档起点年份取整) → (类别, 理由)
    ("Q7209", -178): ("c", "汉朝总条目（Q7209）：皇帝任职记录挂在西汉（Q1072949）/东汉条目下，地图按 china_dynasties 把这段时间解析到西汉、东汉，面板显示正常（china_monarchs 逐年 100%）；扫描单独看总条目才出现空档"),
    ("Q424", 1960): ("c", "1960–1970 年见个案 cambodia_1960；1970 年 10 月起柬埔寨废除君主制（高棉共和国、民主柬埔寨、柬埔寨人民共和国），至 1993 年复辟，Q424 是跨时代的总条目，这段时间本来就没有君主"),
    ("Q209065", 1924): ("c", "希腊第二共和国（1924–1935）：君主制被废除，本来就没有国王；希腊王国条目跨越了共和时期"),
    ("Q29", 1931): ("c", "西班牙第二共和国（1931–1939）与佛朗哥时期：没有君主（1947 年起名义上为王国但王位空悬，佛朗哥为国家元首）"),
    ("Q29", 1873): ("c", "西班牙第一共和国（1873–1874）：没有君主"),
    ("Q12560", 1324): ("c", "奥斯曼一世卒年（1323/1324）与奥尔汗即位年有争议，记录只精确到年"),
    ("Q207521", 1285): ("d", "未记录：达维特一世即位年份（1379/1380/1382）史料不一，无法确定 1381 年的在位者"),
    ("Q83891", 420): ("d", "未记录：421–438 年已由修正后的匹配逻辑覆盖（巴赫拉姆五世）；497–498 年贾马斯普与卡瓦德一世复位的年份（496–499）史料不一"),
    ("Q869", 1610): ("c", "阿瑜陀耶 1655–1656 年柴王、西·素探马拉差短暂在位，年代只精确到年（泰国编年史纪年歧异）"),
    ("Q3446213", 1343): ("d", "未记录：彬牙王国 1340 年代王位更替只见于缅甸编年史，年份各本不一"),
    ("Q282428", 1412): ("d", "未记录（部分）：1421–1422 年萨利赫·穆罕默德、1501 年阿迪勒·图曼贝一世没有可核对的英文维基条目 / Wikidata 条目，未补；1516 年 8–10 月为古里死后到图曼贝二世即位（日期只精确到月）；1517 年 4 月以后为奥斯曼征服"),
    ("Q5343710", 552): ("c", "前后任交接只精确到月（875 年路易二世去世到秃头查理、887 年胖子查理被废到贝伦加尔一世）"),
    ("Q2114397", 1877): ("d", "未记录：哈孟库布沃诺六世 1877 年 7 月去世到七世即位之间的安排，找不到可核对的史料"),
    ("Q171740", 1025): ("d", "未记录：后倭马亚「菲特纳」内乱时期（1009–1031）哈里发频繁更替，1025 年的在位日期史料不一"),
    ("Q207521", 1832): ("d", "未记录：「王子时代」（Zemene Mesafint）傀儡皇帝频繁废立，在位日期只精确到年"),
    ("Q199442", 1164): ("c", "佩德罗尼拉 1164 年退位、阿方索二世 1162 年即继承，记录只精确到年"),
    ("Q2500952", 1442): ("c", "阿瓦王朝 1442 年王位交接只精确到年"),
    ("Q171348", 1709): ("c", "斯坦尼斯瓦夫一世失位与奥古斯特二世复位（1709 年）记录只精确到月"),
    ("Q172107", 1709): ("c", "斯坦尼斯瓦夫一世失位与奥古斯特二世复位（1709 年）记录只精确到月"),
    ("Q207521", 1868): ("c", "1868–1871 年已补特克莱·吉奥尔吉斯二世；剩下的 1868 年 4–5 月为特沃德罗斯二世死后到其即位（日期只精确到月）"),
    ("Q171348", 1501): ("c", "1501 年 6–10 月见个案 poland_1501；剩余为当选到加冕之间（任期按加冕日记录）"),
    ("Q171348", 1506): ("c", "1506 年 8–12 月见个案 poland_1506；剩余为当选到加冕之间（任期按加冕日记录）"),
    ("Q12548", 1208): ("c", "阿道夫被废与阿尔布雷希特一世当选同在 1298 年 6 月（只精确到月）"),
    ("Q12548", 1250): ("c", "阿道夫被废与阿尔布雷希特一世当选同在 1298 年 6 月（只精确到月）"),
    ("Q171150", 1307): ("c", "1342–1382 年已补拉约什一世；剩下的 1382 年 9 月为拉约什去世（9 月 10 日）到玛丽加冕（9 月 17 日）"),
    ("Q165154", 1665): ("c", "1665–1700 年已补卡洛斯二世；剩下的 1700 年 11 月为其去世到费利佩五世（只精确到月）"),
    ("Q12548", 983): ("c", "奥托三世 983 年 6 月已当选国王（12 月加冕），交接只精确到月"),
    ("Q34", 1439): ("c", "1438–1441 年见个案 sweden_1438；剩余为加冕当月"),
    ("Q1145470", 311): ("c", "311–313 年见个案 jin_yongjia；剩余为晋愍帝即位当月（只精确到月）"),
    ("Q1147043", 1276): ("c", "1276 年 2–6 月见个案 song_1276；剩余为端宗即位当月（只精确到月）"),
}
def months(g):
    out = []
    for lo, hi in g["empty_spans"]:
        t = lo + 1 / 24
        while t < hi:
            yy = int(t // 1); mm = min(12, int((t - yy) * 12) + 1)
            if yy != 0: out.append(HDate(yy, mm, 15))
            t += 1 / 12
    return out
res = []; cnt = collections.Counter()
for g in before:
    k = (g["state"], g["office"], g["from"])
    ga = after.get(k)
    if g["cls"]:
        cls, why = g["cls"]; detail = {}
    else:
        offs = [o for o in R.office_by_state.get(g["state"], [])]
        ms = months(g); na = nb = 0; who_a, who_b = collections.Counter(), collections.Counter()
        for d in ms:
            dk = d.key()
            cs = [c for c in newcases.values() if c["id"] in gapcase_ids and g["state"] in c["states"] and iv(dk, c["from"], c["to"])]
            hs = [h for o in offs for h in _holding(o.get("holders", []), dk) if any(f["p"] == h["p"] and f["office"] == o["id"] for f in fix)]
            if cs: nb += 1; who_b.update(c["id"] for c in cs)
            if hs: na += 1; who_a.update((R.persons.get(h["p"]) or {}).get("zh") or h["p"] for h in hs)
        left = ga["empty_months"] if ga and not ga["cls"] else 0
        key2 = (g["state"], int(g["from"] // 1))
        if left and key2 in M and (na + nb) < len(ms) / 2:
            cls, why = M[key2]
        elif na == 0 and nb == 0:
            cls, why = (M.get(key2) or ("c", "修正 leaders._holding 截断逻辑后面板整段都有君主（只精确到年的长期在位记录不再被前任的精确就任日截断）"))
        else:
            cls = "a" if na >= nb else "b"
            why = ("补入缺失的君主任职记录：" + "、".join(x for x, _ in who_a.most_common(8))) if cls == "a" else ("新增空位期/摄政/共治个案：" + "、".join(x for x, _ in who_b.most_common(6)))
            if na and nb: why += "；另有" + ("个案 " + "、".join(x for x, _ in who_b.most_common(4)) if cls == "a" else "补入的君主 " + "、".join(x for x, _ in who_a.most_common(4)))
            if left: why += f"；剩余 {left} 个月：" + (M.get(key2, ("", "交接日期只精确到月"))[1])
        detail = {"empty_months_before": g["empty_months"], "covered_by_holders": na, "covered_by_cases": nb, "empty_months_after": left}
    cnt[cls] += 1
    res.append({"state": g["state"], "state_zh": g["state_zh"], "office": g["office"], "from": g["from"], "to": g["to"], "cls": cls, "reason": why, **detail})
json.dump({"_doc": __doc__, "counts": cnt, "gaps": res}, open("data/audit/gap_resolutions.json", "w"), ensure_ascii=False, indent=1)
print(cnt)
md = open("data/audit/leader_gaps.md", encoding="utf-8").read().split("\n## v0.6.1 逐条核对结果")[0]
md += "\n## v0.6.1 逐条核对结果\n\n" + f"共 {len(res)} 处：a（补缺失君主）{cnt['a']}，b（真实空位/摄政/共治，新增个案）{cnt['b']}，c（日期精度/扫描假象）{cnt['c']}，d（未记录，无法核实）{cnt['d']}。明细见 data/audit/gap_resolutions.json。\n\n| 政权 | 职位 | 空档 | 类别 | 说明 |\n|---|---|---|---|---|\n"
for r in res:
    if r["cls"] != "c" or r.get("empty_months_before"):
        md += f"| {r['state_zh']}（{r['state']}） | {r['office']} | {r['from']:.2f}–{r['to']:.2f} | {r['cls']} | {r['reason']} |\n"
md += f"\n另有 {sum(1 for r in res if r['cls'] == 'c' and not r.get('empty_months_before'))} 处在第 1 步即判为 c（面板本来就显示君主，或空档在政权存续期以外），未逐条列出。\n"
open("data/audit/leader_gaps.md", "w", encoding="utf-8").write(md)
