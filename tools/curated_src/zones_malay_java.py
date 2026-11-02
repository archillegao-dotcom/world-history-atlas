#!/usr/bin/env python3
"""v0.6.1：马来半道诸苏丹国与日惹苏丹国的「政权区」（as_polity）——底图把它们画在英属马来亚 / 荷属东印度
整体之内，面板无法打开这些苏丹国。这里按 Natural Earth 今一级行政区补上可点击的区域（大致范围），
写入 data/curated/control_zones.json（group = princely_states，重复运行会覆盖本组）。
日期依据（英文维基，国际通行叙述）：
- 柔佛：1855-03-10 天猛公阿布巴卡（父）取得柔佛大陆统治权；1885-12-11 英柔条约——英国负责外交并提供保护，
  柔佛仍自治；1914-05-12 接受英国总顾问，成为马来属邦（Unfederated Malay States）之一的英国保护国；
  1942-01-31 日军占领全境。https://en.wikipedia.org/wiki/Johor ；https://en.wikipedia.org/wiki/Unfederated_Malay_States
- 霹雳：1874-01-20 邦咯条约，接受英国驻扎官；1895-07-01 马来联邦成立；1941-12 日军占领。
  https://en.wikipedia.org/wiki/Pangkor_Treaty_of_1874 ；https://en.wikipedia.org/wiki/Federated_Malay_States
- 雪兰莪：1874 年接受英国驻扎官（首任驻扎官 1875 年初到任）；1895-07-01 马来联邦；1942-01-11 日军占领吉隆坡，
  至 1945-09-12。https://en.wikipedia.org/wiki/Selangor
- 日惹：1755 年吉扬地条约建国；1830 年爪哇战争后自治权大减，为荷属东印度的自治土邦（zelfbesturend landschap）；
  1942-03-08 荷属东印度投降，日本占领至 1945-08-17。https://en.wikipedia.org/wiki/Yogyakarta_Sultanate
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "data/curated/control_zones.json"
G = "princely_states"
W = {"jh": "https://en.wikipedia.org/wiki/Johor", "ums": "https://en.wikipedia.org/wiki/Unfederated_Malay_States",
     "pk": "https://en.wikipedia.org/wiki/Pangkor_Treaty_of_1874", "fms": "https://en.wikipedia.org/wiki/Federated_Malay_States",
     "sl": "https://en.wikipedia.org/wiki/Selangor", "jo": "https://en.wikipedia.org/wiki/Japanese_occupation_of_Malaya",
     "yg": "https://en.wikipedia.org/wiki/Yogyakarta_Sultanate", "jdei": "https://en.wikipedia.org/wiki/Japanese_occupation_of_the_Dutch_East_Indies"}
NOTE = "范围取 Natural Earth 今一级行政区（大致范围）；底图把该地画在英属马来亚 / 荷属东印度整体之内，这里补上可点击的苏丹国。"


def z(id_, qid, zh_state, name_zh, name_en, frm, until, geom, dates_note, src):
    return {"id": id_, "group": G, "kind": "regime", "as_polity": True, "name_zh": name_zh, "name_en": name_en,
            "controller": {"qid": qid, "zh": zh_state}, "from": frm, "until": until, "approx": True,
            "dates_note": dates_note, "sources": [W[s] for s in src], "note": NOTE, "geometry": geom}


JH, PK, SL, YG = "Q183032", "Q188953", "Q189710", "Q2114397"
gj, gp, gs, gy = {"admin1": ["MY-01"]}, {"admin1": ["MY-08"]}, {"admin1": ["MY-10", "MY-14", "MY-16"]}, {"admin1": ["ID-YO"]}
ZONES = [
    z("johor_1855", JH, "柔佛苏丹国", "柔佛（自治苏丹国，英国影响下）", "Johor (self-governing, under British influence)", "1855-03-10", "1885-12-11", gj,
      "1855-03-10 天猛公取得柔佛大陆统治权；与海峡殖民地关系密切但仍自治；1885-12-11 英柔条约后由英国负责外交。", ["jh"]),
    z("johor_1885", JH, "柔佛苏丹国", "柔佛苏丹国（英国保护，外交由英国负责）", "Sultanate of Johor (British protection, 1885 treaty)", "1885-12-11", "1914-05-12", gj,
      "1885-12-11 英柔条约：英国负责外交并提供保护，内政自治；1914-05-12 接受英国总顾问，成为马来属邦。", ["jh"]),
    z("johor_1914", JH, "柔佛苏丹国", "柔佛苏丹国（英国保护国，马来属邦）", "Sultanate of Johor (Unfederated Malay State)", "1914-05-12", "1942-01-31", gj,
      "1914-05-12 起为英国保护国（马来属邦）；1942-01-31 日军占领柔佛全境。", ["jh", "ums", "jo"]),
    z("perak_1874", PK, "霹雳苏丹国", "霹雳苏丹国（英国驻扎官制度）", "Sultanate of Perak (British Residential system)", "1874-01-20", "1895-07-01", gp,
      "1874-01-20 邦咯条约：接受英国驻扎官，苏丹仍为名义君主；1895-07-01 加入马来联邦。", ["pk"]),
    z("perak_1895", PK, "霹雳苏丹国", "霹雳苏丹国（英国保护国，马来联邦）", "Sultanate of Perak (Federated Malay States)", "1895-07-01", "1941-12", gp,
      "1895-07-01 起为马来联邦成员（英国保护国）；1941 年 12 月日军占领。", ["fms", "jo"]),
    z("selangor_1874", SL, "雪兰莪苏丹国", "雪兰莪苏丹国（英国驻扎官制度）", "Sultanate of Selangor (British Residential system)", "1874", "1895-07-01", gs,
      "1874 年苏丹阿卜杜勒·萨马德接受英国驻扎官（首任驻扎官 1875 年初到任）；1895-07-01 加入马来联邦。", ["sl"]),
    z("selangor_1895", SL, "雪兰莪苏丹国", "雪兰莪苏丹国（英国保护国，马来联邦）", "Sultanate of Selangor (Federated Malay States)", "1895-07-01", "1942-01-11", gs,
      "1895-07-01 起为马来联邦成员；1942-01-11 日军占领吉隆坡。", ["fms", "sl", "jo"]),
    z("selangor_1942", SL, "雪兰莪苏丹国", "雪兰莪（日本占领下）", "Selangor (Japanese occupation)", "1942-01-11", "1945-09-12", gs,
      "1942-01-11 日军占领吉隆坡；日方另立苏丹（见面板的空位期/对立君主案例）；1945-09-12 日军在新加坡投降。", ["sl", "jo"]),
    z("yogya_1830", YG, "日惹苏丹国", "日惹苏丹国（荷属东印度自治土邦）", "Sultanate of Yogyakarta (self-governing principality, Dutch East Indies)", "1830-03-28", "1942-03-08", gy,
      "1755 年建国；1830 年爪哇战争结束后大片领土被荷兰吞并，作为荷属东印度的自治土邦保留；1942-03-08 荷属东印度投降。", ["yg"]),
    z("yogya_1942", YG, "日惹苏丹国", "日惹苏丹国（日本占领下）", "Sultanate of Yogyakarta (Japanese occupation)", "1942-03-08", "1945-08-17", gy,
      "1942-03-08 荷属东印度投降，日本占领；1945-08-17 印度尼西亚宣布独立，苏丹随即宣布日惹归属共和国。", ["yg", "jdei"]),
]

d = json.loads(P.read_text(encoding="utf-8"))
d["zones"] = [x for x in d["zones"] if x.get("group") != G] + ZONES
P.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"{G}: {len(ZONES)} zones; total {len(d['zones'])}")
