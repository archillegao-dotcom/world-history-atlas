"""第四批：明确的单一继承改成当时政权并标注，更晚年份的正文按所选日期截断。

用法：WHA_PORT=8792 python3 tools/accept/next_batch4.py
"""
import json, os, sys, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.modules.treaty_time import leaked_years

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    q = "?" + urllib.parse.urlencode(kw) if kw else ""
    return json.load(urllib.request.urlopen(B + path + q, timeout=180))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + str(got)[:240])
    if not cond:
        fails.append(label)


def party_bits(rec):
    return [(p.get("name") or "", p.get("note") or "") for p in rec.get("parties") or []]


def names(rec):
    return [n for n, _ in party_bits(rec)]


# 文号里的斜线年份不是日期。
check("CETS/2002 不当成 2002 年", 2002 not in leaked_years("欧洲委员会第CETS/2002号", 2001, set()), "ok")
check("旧式四位年仍算年份", 1995 in leaked_years("1995年审议", 1970, set()), "ok")

loc = get("/api/locate", date="1929-02-11", lat="41.90", lon="12.48")
sp = get("/api/modules/spirits", date="1929-02-11", snap=loc["snapshot"], fid=loc["polity"]["fid"])
card = json.dumps(sp, ensure_ascii=False)
check("1929 年罗马的外交卡写着后来由意大利继承", "后来由意大利继承" in card, loc["polity"].get("name"))

lateran = get("/api/treaty/Q193270", date="1929-02-11")
bits = party_bits(lateran)
check("拉特兰显示意大利王国", any(n == "意大利王国" and note == "后来由意大利继承" for n, note in bits), bits)
check("拉特兰不再把意大利共和国列成签署方", "意大利" not in names(lateran), names(lateran))
check("拉特兰所属国家不单写意大利", "意大利" not in (lateran.get("countries") or []), lateran.get("countries"))

lausanne = get("/api/treaty/Q193258", date="1923-07-24")
bits = party_bits(lausanne)
check(
    "洛桑显示塞尔维亚、克罗地亚和斯洛文尼亚王国并标注继承",
    any("塞尔维亚、克罗地亚和斯洛文尼亚" in n and note == "后来由南斯拉夫王国继承" for n, note in bits),
    bits,
)
check("洛桑不再另列南斯拉夫王国", not any(n == "南斯拉夫王国" for n, _ in bits), names(lausanne))

hub = get("/api/treaty/Q698686", date="1763-02-15")
check(
    "胡贝图斯堡显示萨克森选帝侯",
    any(n == "萨克森选帝侯" and "后来由萨克森王国继承" in note for n, note in party_bits(hub)),
    party_bits(hub),
)

london = get("/api/treaty/Q1160895", date="1839-04-19")
check(
    "1839 伦敦条约显示七月王朝",
    any(n == "七月王朝" and note == "后来由法兰西第二共和国继承" for n, note in party_bits(london)),
    party_bits(london),
)

paris = get("/api/treaty/Q183080", date="1883-03-20")
check(
    "巴黎公约显示意大利王国",
    any(n == "意大利王国" and note == "后来由意大利继承" for n, note in party_bits(paris)),
    party_bits(paris),
)

anglo = get("/api/treaty/Q1342523", date="1854-10-14")
check("1854 日英和亲条约不改成第二尚氏", all("第二尚氏" not in n for n in names(anglo)), names(anglo))

marpol = get("/api/treaty/Q651219", date="1973-11-02")
mn = names(marpol)
check("防污公约仍列纳米比亚", any("纳米比亚" in n for n in mn), "n=" + str(len(mn)))
check("防污公约不改写成西南非", all("西南非" not in n for n in mn) and not any(note for _, note in party_bits(marpol)), "notes")

npt_early = get("/api/treaty/Q186444", date="1970-03-05")
npt_later = get("/api/treaty/Q186444", date="1995-05-12")
early = (npt_early.get("summary") or {}).get("extract") or ""
later = (npt_later.get("summary") or {}).get("extract") or ""
check("不扩散条约 1970 年不显示 1995", "1995" not in early, early[:180])
check("不扩散条约 1995 年显示延期", "1995" in later, later[:180])

sea = get("/api/treaty/Q622649", date="1986-02-28")
sea_text = (sea.get("summary") or {}).get("extract") or ""
check("单一欧洲法案仍保留 1992 年底期限", "1992" in sea_text, sea_text[:180])

rome = get("/api/treaty/Q167457", date="1958-01-01")
rome_later = get("/api/treaty/Q167457", date="2009-12-01")
check("罗马条约 1958 年不显示 2009", "2009" not in ((rome.get("summary") or {}).get("extract") or ""), "ok")
check("罗马条约 2009 年显示更名", "2009" in ((rome_later.get("summary") or {}).get("extract") or ""), "ok")

# 1951 年的海上人命安全公约仍是 1948 年版，不混入 1974。
solas = get("/api/treaty/curated:solas-1948", date="1951-03-16")
blob = json.dumps(solas, ensure_ascii=False)
check("1951 仍能打开 1948 年版", "1974" not in blob and not solas.get("withhold"), solas.get("view_status"))

print(f"\n{len(fails)} failed" if fails else "\n0 failed")
sys.exit(1 if fails else 0)
