#!/usr/bin/env python3
"""
官方来源的历任首长名单（补充 Wikidata 缺失的任职者/任期）。可断点续跑：网页缓存在 data/cache/official/，
每次请求间隔 ≥ 1.5 秒；已缓存的页面不再请求（WHA_REFRESH=1 强制刷新）。

每条记录：{name, from, to, src(官方网页 URL), precision}；日期只取网页上写明的，没有的留空（面板显示「未记录」），不推测。
输出 data/official_offices.json.gz：{office_qid: {state, office_zh, source_name, source_url, holders:[...]}}，
以及 data/audit/official_coverage.json（关键职位 Wikidata 原有 vs 合并后的覆盖率）。
运行时（backend/polity.py）把这些记录并入同一职位：Wikidata 已有该人且有任期的保持不变；Wikidata 有该人但缺任期的
补上官方任期；Wikidata 没有的人另加一条（人物名称取官方名单，标注来源）。

已实现的来源（其余国家见 AUDIT_REPORT.md「已知缺口」）：
  中华民国 立法院院长   立法院全球资讯网「历届院长」各届详情页（任职期间，民国纪年，精确到日）
  中华民国 总统         总统府「行宪后历任总统」（精确到年，只做核对）
  日本 内阁总理大臣     首相官邸「历代内阁」（任期，和历，精确到日）
  英国 首相             GOV.UK「Past Prime Ministers」（精确到年，只做核对/补缺）
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from wdsparql import DATA, simplifier  # noqa: E402

CACHE = DATA / "cache" / "official"
UA = "Mozilla/5.0 (WorldHistoryAtlas/0.5 educational offline atlas; polite crawler, 1 request / 1.5 s)"
t2s = simplifier()
_last = [0.0]


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".html")
    if f.exists() and os.environ.get("WHA_REFRESH") != "1":
        return f.read_text(encoding="utf-8", errors="ignore")
    wait = 1.5 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    for attempt in range(3):
        try:
            html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "ignore")
            break
        except Exception as e:  # noqa: BLE001
            print("  retry", url, e, flush=True)
            time.sleep(5 * (attempt + 1))
    else:
        # 少数政府网站的证书链 Python 无法验证（如 president.gov.tw「Missing Subject Key Identifier」）：改用系统 curl
        import subprocess
        try:
            html = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, url], capture_output=True, timeout=60).stdout.decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            return ""
    _last[0] = time.time()
    f.write_text(html, encoding="utf-8")
    return html


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>", " ", html)))


def T(y, m=None, d=None):
    return {"y": y, "m": m or 0, "d": d or 0, "p": 11 if d else (10 if m else 9)}


# ------------------------------------------------------------------ 中华民国 立法院院长
def roc_ly_speakers():
    base = "https://www.ly.gov.tw"
    lst = fetch(base + "/Pages/List.aspx?nodeid=6569")
    out = []
    for href, title in re.findall(r'<a[^>]+href="(/Pages/Detail\.aspx\?nodeid=6569&(?:amp;)?pid=\d+)"[^>]*title="(第\d+屆院長 [^"]+)"', lst):
        url = base + href.replace("&amp;", "&")
        t = text(fetch(url))
        name = title.split(" ", 1)[1].strip()
        m = re.search(r"任職期間\s*(\d+)年(\d+)月(\d+)日\s*(?:起)?\s*(?:至\s*(\d+)年(\d+)月(\d+)日)?", t)
        rec = {"name": name, "name_zh": t2s(name), "term": title.split(" ")[0], "src": url}
        if m:
            g = m.groups()
            rec["from"] = T(int(g[0]) + 1911, int(g[1]), int(g[2]))
            if g[3]:
                rec["to"] = T(int(g[3]) + 1911, int(g[4]), int(g[5]))
        out.append(rec)
    # 现任院长（「院长」页）
    cur_url = base + "/Pages/List.aspx?nodeid=120"
    cur = text(fetch(cur_url))
    m = re.search(r"院長\s+院長\s+([\u4e00-\u9fff]{2,4})\s.*?屆別：第\s*(\d+)\s*屆.*?到職日期：(\d+)年(\d+)月(\d+)日", cur)
    if m and not any(r["name"] == m.group(1) for r in out):
        g = m.groups()
        out.insert(0, {"name": g[0], "name_zh": t2s(g[0]), "term": f"第{g[1]}屆院長", "src": cur_url,
                       "from": T(int(g[2]) + 1911, int(g[3]), int(g[4]))})
    return {"office": "Q7241342", "state": "Q865", "office_zh": "立法院院长", "source_name": "立法院全球资讯网「历届院长」",
            "source_url": base + "/Pages/List.aspx?nodeid=6569", "holders": out}


# ------------------------------------------------------------------ 中华民国 总统（年份）
def roc_presidents():
    url = "https://www.president.gov.tw/Page/81"
    t = text(fetch(url))
    out = []
    for m in re.finditer(r"第([\d~]+)任\s+([\u4e00-\u9fff]{1,2})總統([\u4e00-\u9fff]{1,3})(?:先生|女士).*?民國\s*\d+\s*-\s*\d*\s*年\s*\((\d{4})\s*-\s*(\d{4})?\s*\)", t):
        term, sur, given, a, b = m.groups()
        name = sur + given
        out.append({"name": name, "name_zh": t2s(name), "term": f"第{term}任", "from": T(int(a)), "to": T(int(b)) if b else None,
                    "src": url, "check_only": True})
    return {"office": "Q887003", "state": "Q865", "office_zh": "中华民国总统", "source_name": "中华民国总统府「行宪后历任总统」",
            "source_url": url, "holders": out}


# ------------------------------------------------------------------ 日本 内阁总理大臣
ERA = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}


def jdate(era, y, m, d):
    yy = 1 if y == "元" else int(y)
    return T(ERA[era] + yy, int(m), int(d))


def japan_pms():
    url = "https://www.kantei.go.jp/jp/rekidainaikaku/index.html"
    t = text(fetch(url))
    out = []
    pat = re.compile(r"第(\d+)代\s+([\u3040-\u30ff\u4e00-\u9fff々]+)\s+([\u3040-\u30ff\u4e00-\u9fff々]+)\s+在職日数\s*[\d,]+\s*日\s*"
                     r"(明治|大正|昭和|平成|令和)(元|\d+)年(\d+)月(\d+)日[～~]((明治|大正|昭和|平成|令和)(元|\d+)年(\d+)月(\d+)日)?")
    for m in pat.finditer(t):
        g = m.groups()
        name = g[1] + g[2]
        rec = {"name": name, "name_zh": t2s(name), "term": f"第{g[0]}代", "from": jdate(g[3], g[4], g[5], g[6]), "src": url}
        if g[7]:
            rec["to"] = jdate(g[8], g[9], g[10], g[11])
        out.append(rec)
    return {"office": "Q274948", "state": "Q17", "office_zh": "日本内阁总理大臣", "source_name": "日本首相官邸「歴代内閣」",
            "source_url": url, "holders": out}


# ------------------------------------------------------------------ 英国 首相（年份）
def uk_pms():
    url = "https://www.gov.uk/government/history/past-prime-ministers"
    html = fetch(url)
    out = []
    # 每位首相一个卡片：<h3 ...>姓名</h3> ... 若干「YYYY to YYYY」
    for blk in re.split(r"<h3", html)[1:]:
        nm = re.sub(r"<[^>]+>", "", blk.split("</h3>", 1)[0].split(">", 1)[-1]).strip()
        rest = text(blk.split("</h3>", 1)[-1])[:300]
        spans = re.findall(r"(\d{4}) to (\d{4})", rest.split("The Rt Hon")[0])
        if not nm or not spans:
            continue
        clean = re.sub(r"^(The Rt Hon |Sir |Lord |Baroness |The Earl of |The Marquess of |The Duke of |Viscount )+", "", nm)
        clean = re.sub(r"\s+(KG|CH|MP|OM|PC|KT|GCB)\b.*$", "", clean).strip()
        for a, b in spans:
            out.append({"name": nm, "name_en": clean, "from": T(int(a)), "to": T(int(b)) if int(b) < 2100 else None,
                        "src": url, "check_only": True})
    return {"office": "Q14211", "state": "Q145", "office_zh": "英国首相", "source_name": "GOV.UK「Past Prime Ministers」",
            "source_url": url, "holders": out}


# ------------------------------------------------------------------ 法国 总统（爱丽舍宫官网，年份，只做核对）
def fr_presidents():
    url = "https://www.elysee.fr/la-presidence/les-presidents-de-la-republique"
    t = text(fetch(url)).replace("&#039;", "'")
    out = []
    i = t.find("Cinquième République Emmanuel Macron")
    body = t[i:] if i >= 0 else t
    m = re.search(r"Emmanuel Macron Mandat en cours", body)
    if m:
        out.append({"name": "Emmanuel Macron", "name_en": "Emmanuel Macron", "from": T(2017), "src": url, "check_only": True})
    for nm, a, b in re.findall(r"([A-ZÉ][\w'’\- ]{3,40}?) (1[89]\d\d|20\d\d) - (1[89]\d\d|20\d\d)", body):
        nm = re.sub(r"^(.*Mandat en cours |République )", "", nm.strip())
        out.append({"name": nm, "name_en": nm, "from": T(int(a)), "to": T(int(b)), "src": url, "check_only": True})
    return {"office": "Q191954", "state": "Q142", "office_zh": "法国总统", "source_name": "爱丽舍宫「Les présidents de la République」",
            "source_url": url, "holders": out}


# ------------------------------------------------------------------ 美国 国务卿（国务院历史学家办公室，年份，只做核对）
def us_secstate():
    url = "https://history.state.gov/departmenthistory/people/principalofficers/secretary"
    t = text(fetch(url))
    out = []
    for nm, a, b in re.findall(r"([A-Z][A-Za-z.\- ]{4,60}?(?: Jr\.)?) \((\d{4})(?:–(\d{4}|present))?\)", t):
        nm = nm.strip()
        out.append({"name": nm, "name_en": nm, "from": T(int(a)), "to": T(int(b)) if b and b.isdigit() else None,
                    "src": url, "check_only": True})
    return {"office": "Q14213", "state": "Q30", "office_zh": "美国国务卿", "source_name": "美国国务院历史学家办公室「Secretaries of State」",
            "source_url": url, "holders": out}


# ------------------------------------------------------------------ 澳门总督（英文维基百科「Governor of Macau」历任表，精确到日的才新增）
MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"])}


def endate(s):
    s = re.sub(r"<[^>]+>|\{\{[^}]*\}\}", "", s or "").strip()
    m = re.match(r"(\d{1,2}) (\w+) (\d{4})$", s)
    if m and m.group(2) in MONTHS:
        return T(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    m = re.match(r"(\w+) (\d{4})$", s)
    if m and m.group(1) in MONTHS:
        return T(int(m.group(2)), MONTHS[m.group(1)])
    m = re.match(r"(\d{4})$", s)
    return T(int(m.group(1))) if m else None


def macau_governors():
    page = "https://en.wikipedia.org/wiki/Governor_of_Macau"
    api = "https://en.wikipedia.org/w/api.php?action=parse&page=Governor_of_Macau&prop=wikitext&format=json&formatversion=2"
    wt = json.loads(fetch(api))["parse"]["wikitext"]
    rows = []
    for row in wt.split("|-")[1:]:
        cells = [c.strip() for c in re.split(r"\|\||\n\|", row) if c.strip()]
        links = [x for x in re.findall(r"\[\[(?!File:)([^\]|]+)(?:\|[^\]]*)?\]\]", row)
                 if not re.search(r"Council|Senate|Leal Senado|Government of", x)]   # 「澳门议事会」等机构不是人
        if not links:
            continue
        acting = "acting" in row or "interim" in row
        tail = [c for c in cells if not c.startswith("[[") and "bgcolor" not in c and not c.startswith("[[File")]
        dates = [c.split("|")[-1].strip() for c in tail if re.search(r"\d{4}", c)]
        if len(dates) < 1:
            continue
        a = endate(dates[0])
        b = endate(dates[1]) if len(dates) > 1 else None
        if 'colspan="2"' in row:
            b = a
        rows.append((links[0], a, b, acting))
    # 维基条目名 → Wikidata QID 与中文名
    from wdsparql import sparql
    titles = " ".join('"%s"@en' % t.replace('"', '') for t, *_ in rows)
    q = ("SELECT ?t ?p ?zh WHERE { VALUES ?t { %s } ?a schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t ."
         " OPTIONAL { ?p rdfs:label ?zh FILTER(lang(?zh)='zh') } }") % titles
    qid = {}
    for x in sparql(q):
        qid[x["t"]["value"]] = (x["p"]["value"].rsplit("/", 1)[-1], (x.get("zh") or {}).get("value"))
    out = []
    for t, a, b, acting in rows:
        if not a:
            continue
        q_, zh = qid.get(t, (None, None))
        out.append({"name": t, "name_en": t, "name_zh": t2s(zh) if zh else None, "qid": q_, "from": a, "to": b,
                    "acting": acting, "src": page})
    return {"office": "Q907213", "state": "Q3916279", "office_zh": "澳门总督", "source_name": "英文维基百科「Governor of Macau」历任总督表（CC BY-SA）",
            "source_url": page, "holders": out}


# ------------------------------------------------------------------ Wikidata P39 任职声明（Wikidata 职位条目中有、但本地职位缺任期的）
def wikidata_p39(office, state, office_zh):
    def fn():
        from wdsparql import sparql
        q = ("SELECT ?p ?en ?zh ?s ?sp ?e ?ep WHERE { ?p p:P39 ?st . ?st ps:P39 wd:%s . "
             "OPTIONAL { ?st pqv:P580 ?sv . ?sv wikibase:timeValue ?s ; wikibase:timePrecision ?sp } "
             "OPTIONAL { ?st pqv:P582 ?ev . ?ev wikibase:timeValue ?e ; wikibase:timePrecision ?ep } "
             "OPTIONAL { ?p rdfs:label ?en FILTER(lang(?en)='en') } OPTIONAL { ?p rdfs:label ?zh FILTER(lang(?zh)='zh') } }") % office

        def wt(v, pr):
            if not v:
                return None
            m = re.match(r"(-?\d+)-(\d\d)-(\d\d)", v["value"])
            p_ = int(pr["value"]) if pr else 9
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return {"y": y, "m": mo if p_ >= 10 else 0, "d": d if p_ >= 11 else 0, "p": min(p_, 11)}
        out, seen = [], set()
        for x in sparql(q):
            pid = x["p"]["value"].rsplit("/", 1)[-1]
            a = wt(x.get("s"), x.get("sp"))
            k = (pid, a and a["y"])
            if k in seen:
                continue
            seen.add(k)
            out.append({"name": (x.get("en") or {}).get("value") or pid, "name_en": (x.get("en") or {}).get("value"),
                        "name_zh": t2s(x["zh"]["value"]) if x.get("zh") else None, "qid": pid, "from": a,
                        "to": wt(x.get("e"), x.get("ep")), "src": f"https://www.wikidata.org/wiki/{pid}"})
        out = [r for r in out if r["from"]]
        return {"office": office, "state": state, "office_zh": office_zh, "source_name": f"Wikidata {office} 的 P39 任职声明（起止限定）",
                "source_url": f"https://www.wikidata.org/wiki/{office}", "holders": out, "kind": "wikidata"}
    fn.__name__ = f"wikidata_p39_{office}"
    return fn


# ------------------------------------------------------------------ 维基百科 {{Officeholder table}} 模板表（英文维基历任表的通用格式）
def wiki_officeholder(page, office, state, office_zh):
    def fn():
        api = f"https://en.wikipedia.org/w/api.php?action=parse&page={page}&prop=wikitext&format=json&formatversion=2"
        wt = json.loads(fetch(api))["parse"]["wikitext"]
        rows = []
        for blk in wt.split("{{Officeholder table")[1:]:
            f = dict(re.findall(r"\|\s*(officeholder|term_start|term_end)\s*=\s*([^\n]*)", blk))
            m = re.search(r"\[\[([^\]|]+)", f.get("officeholder", ""))
            if not m:
                continue
            a = endate(re.sub(r"\[\[[^\]]*\]\]|\{\{[^}]*\}\}|†", "", f.get("term_start", "")).strip())
            b = endate(re.sub(r"\[\[[^\]]*\]\]|\{\{[^}]*\}\}|†", "", f.get("term_end", "")).strip())
            rows.append((m.group(1), a, b))
        from wdsparql import sparql
        titles = " ".join('"%s"@en' % t.replace('"', '') for t, *_ in rows)
        q = ("SELECT ?t ?p ?zh WHERE { VALUES ?t { %s } ?a schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t ."
             " OPTIONAL { ?p rdfs:label ?zh FILTER(lang(?zh)='zh') } }") % titles
        qid = {x["t"]["value"]: (x["p"]["value"].rsplit("/", 1)[-1], (x.get("zh") or {}).get("value")) for x in sparql(q)}
        url = f"https://en.wikipedia.org/wiki/{page}"
        out = [{"name": t, "name_en": t, "name_zh": t2s(qid[t][1]) if qid.get(t, (0, 0))[1] else None, "qid": qid.get(t, (None,))[0],
                "from": a, "to": b, "src": url} for t, a, b in rows if a]
        return {"office": office, "state": state, "office_zh": office_zh, "source_name": f"英文维基百科「{page.replace('_', ' ')}」历任表（CC BY-SA）",
                "source_url": url, "holders": out}
    fn.__name__ = f"wiki_{office}"
    return fn


# 重点国家（中华民国、中华人民共和国、美、英、法、德、俄/苏、日、韩）的关键职位：本地数据缺任期时用 Wikidata P39 声明补
WD_FILL = [("Q462189", "Q15180", "苏联部长会议主席"), ("Q1048744", "Q15180", "苏联共产党中央委员会总书记"),
           ("Q2708520", "Q148", "中国共产党中央委员会主席"), ("Q655407", "Q148", "中华人民共和国主席"),
           ("Q4122271", "Q148", "中华人民共和国国务院总理"), ("Q849418", "Q148", "中国共产党中央委员会总书记"),
           ("Q887003", "Q865", "中华民国总统"), ("Q11696", "Q30", "美国总统"), ("Q15407843", "Q884", "大韩民国国务总理"),
           ("Q218295", "Q159", "俄罗斯总统")]

SOURCES = [roc_ly_speakers, roc_presidents, japan_pms, uk_pms, fr_presidents, us_secstate, macau_governors] + \
          [wikidata_p39(*x) for x in WD_FILL] + \
          [wiki_officeholder("Premier_of_the_Soviet_Union", "Q462189", "Q15180", "苏联部长会议主席"),
           wiki_officeholder("General_Secretary_of_the_Communist_Party_of_the_Soviet_Union", "Q1048744", "Q15180", "苏联共产党中央委员会总书记"),
           wiki_officeholder("Chancellor_of_Germany", "Q56022", "Q183", "德国联邦总理"),
           wiki_officeholder("President_of_Germany", "Q25223", "Q183", "德国联邦总统"),
           wiki_officeholder("President_of_South_Korea", "Q6296418", "Q884", "韩国总统"),
           wiki_officeholder("Prime_Minister_of_Russia", "Q842386", "Q159", "俄罗斯总理")]


def main():
    out = {}
    for fn in SOURCES:
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            print(fn.__name__, "FAILED", e, flush=True)
            continue
        if r["office"] in out:      # 同一职位有多个来源（如官方名单 + Wikidata P39）：分开存放
            out[r["office"] + "#" + fn.__name__] = r
        else:
            out[r["office"]] = r
        print(f"{fn.__name__}: {len(r['holders'])} records", flush=True)
    (DATA / "official_offices.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False).encode("utf-8")))
    print("wrote official_offices.json.gz")


if __name__ == "__main__":
    main()
