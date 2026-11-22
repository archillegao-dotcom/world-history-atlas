#!/usr/bin/env python3
"""晋系、新桂系：把省级实控落到 1931 年 MCGD 县域。

几何只用 data/curated/geom/roc_county_cells.geojson（治所泰森多边形，已裁在 ENP 省界上）。
不使用今天的行政区划，也不使用 CHGIS。

缺县名单的时段不新造县界：整批落到治所上的标「大致」，没有任何名单的标「待考」并且不填色。
已核对的城陷日只来自仓库里已经对过印页的记载，不在这里新解一页。

用法：python3 tools/build_faction_counties.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CELLS = ROOT / "data" / "curated" / "geom" / "roc_county_cells.geojson"
ZONES = ROOT / "data" / "curated" / "control_zones.json"
OUT = ROOT / "data" / "curated" / "roc_faction_counties.json"

ZENODO = "https://zenodo.org/records/5721459"
V26 = "https://www.drnh.gov.tw/p/404-1003-13312.php?Lang=zh-tw"
V27 = "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw"
V28B = "https://www.drnh.gov.tw/p/404-1003-13317.php?Lang=zh-tw"
V29B = "https://www.drnh.gov.tw/p/404-1003-13320.php?Lang=zh-tw"
V33 = "https://www.drnh.gov.tw/p/404-1003-13334.php?Lang=zh-tw"
V38 = "https://www.drnh.gov.tw/p/404-1003-13361.php?Lang=zh-tw"
V13 = "https://www.drnh.gov.tw/p/404-1003-13280.php?Lang=zh-tw"
V14 = "https://www.drnh.gov.tw/p/404-1003-13282.php?Lang=zh-tw"
WIKI_YAN = "https://zh.wikipedia.org/wiki/阎锡山"
WIKI_ZY = "https://zh.wikipedia.org/wiki/中原大战"
WIKI_GUI = "https://zh.wikipedia.org/wiki/桂系"

# 克复日之后标晋系，只到下一份更具体的名单。克复当天不含在日军区间里（until 排他）。
RECOVERED = [
    ("mcgd:s1016", "1938-07-30", "晋城", "民国二十七年七月至十二月，印页一八二，本日克复晋城。"),
    ("mcgd:s1759", "1938-07-30", "阳城", "民国二十七年七月至十二月，印页一八二，本日克复阳城。"),
    ("mcgd:s1759", "1939-07-25", "阳城", "民国二十八年七月至十二月，印页八三（PDF 第91页），追述二十五日晨克复阳城。"),
    ("mcgd:s1051", "1938-07-30", "沁水", "民国二十七年七月至十二月，印页一八二，本日克复沁水。"),
    ("mcgd:s1051", "1939-07-26", "沁水", "民国二十八年七月至十二月，印页八三（PDF 第91页），迄二十六日晚克复沁水。"),
    ("mcgd:s1045", "1938-08-03", "翼城", "民国二十七年七月至十二月，印页二一五，本日攻克翼城。"),
    ("mcgd:s797", "1939-07-11", "武乡", "民国二十八年七月至十二月，印页三七（PDF 第45页），追述十一日克复武乡。"),
    ("mcgd:s35", "1939-07-12", "襄垣", "民国二十八年七月至十二月，印页三七（PDF 第45页），本日晨襄垣克复。"),
    ("mcgd:s78", "1939-08-02", "林县", "民国二十八年七月至十二月，印页一一五（PDF 第122页），追述二日克复林县。"),
]


def load_cells():
    feats = json.loads(CELLS.read_text(encoding="utf-8"))["features"]
    out = {}
    for f in feats:
        p = f["properties"]
        if p["province"] == "山西":
            prov = "shanxi"
        elif p["province"] == "廣西":
            prov = "guangxi"
        else:
            continue
        out[p["id"]] = {
            "id": p["id"],
            "name": p["name"],
            "province": prov,
            "lon": p["lon"],
            "lat": p["lat"],
        }
    return out


def zone_actual(zone: dict) -> str:
    zh = (zone.get("controller") or {}).get("zh") or ""
    name = zone.get("name_zh") or ""
    if "日本" in zh or name.startswith("日军"):
        return "日军占领"
    return zh or name


def collect_zone_spans(cells: dict) -> dict[str, list]:
    zones = json.loads(ZONES.read_text(encoding="utf-8"))["zones"]
    by = {cid: [] for cid in cells}
    for zone in zones:
        if zone.get("group") != "sino_japanese_war":
            continue
        ids = (zone.get("geometry") or {}).get("roc_counties") or []
        if not ids:
            continue
        hit = [i for i in ids if i in by]
        if not hit:
            continue
        one = len(ids) == 1
        note = zone.get("note") or ""
        verified = one and ("已核對" in note or "已核对" in note)
        certainty = "已核对" if verified else "大致"
        text = (
            f"这一县在既有层 {zone['id']} 的县名单里。"
            + ("单县，记载写已核对。" if verified else "名单是既有占领层或边区层，大致，不是这一批新核的页。")
        )
        if zone.get("dates_note"):
            text += zone["dates_note"]
        span = {
            "from": zone["from"],
            "until": zone.get("until") or "1945-08-16",
            "actual": zone_actual(zone),
            "certainty": certainty,
            "note": text,
            "sources": list(zone.get("sources") or []),
            "priority": 40 if verified else 30,
            "paint": None,
        }
        for cid in hit:
            by[cid].append(span)
    return by


def add(bucket, cid, **span):
    bucket[cid].append(span)


def resolve(spans: list) -> list:
    """按日切开，同一天取得分最高的一条。相邻且内容相同的再并上。"""
    if not spans:
        return []
    cuts = sorted({s["from"] for s in spans} | {s["until"] for s in spans})
    picked = []
    for a, b in zip(cuts, cuts[1:]):
        if not (a < b):
            continue
        live = [s for s in spans if s["from"] <= a and b <= s["until"]]
        if not live:
            continue
        best = max(live, key=lambda s: (s["priority"], s["from"]))
        row = {
            "from": a,
            "until": b,
            "actual": best["actual"],
            "certainty": best["certainty"],
            "note": best["note"],
            "sources": best["sources"],
            "paint": best["paint"],
        }
        prev = picked[-1] if picked else None
        if prev and prev["until"] == a and all(
            prev[k] == row[k] for k in ("actual", "certainty", "note", "sources", "paint")
        ):
            prev["until"] = b
            continue
        picked.append(row)
    return picked


def main():
    cells = load_cells()
    spans = collect_zone_spans(cells)
    shanxi = [c for c in cells.values() if c["province"] == "shanxi"]
    guangxi = [c for c in cells.values() if c["province"] == "guangxi"]

    notes = {
        "jin-prewar": {
            "note": (
                "1917-09-01至1937-09-13，落在山西这一块 ENP 省界里的 1931 年治所都标晋系，大致，不是逐县核实。"
                "1912至1917-09-01督军到任日没有锁，不画。"
                "1930年中原大战以后不把河北、察哈尔、绥远写成晋系，县界易手待考。"
                "大同从1937-09-13起另行记载。没有更早陷落日的县，这一批大致晋系收到1937-11-12，不含当天。"
                "未逐县核对《中華民國史事紀要》。"
            ),
            "sources": [WIKI_YAN, WIKI_ZY, ZENODO],
        },
        "jin-gap-war": {
            "note": (
                "1937-11-12至1945-08-16，这一县不在已核对的城陷、既有占领层县名单或晋察冀、晋冀鲁豫、晋绥的县名单里。"
                "标待考，不画成晋系，也不画成共军。"
            ),
            "sources": [ZENODO],
        },
        "jin-gap-late": {
            "note": (
                "1945-08-16至1949-04-24只锁阳曲为晋系。这一县没有收缩名单，标待考，不画。"
                "不把太原周边写成已经沦陷，也不写成仍由晋系控制。"
            ),
            "sources": [V38, ZENODO],
        },
        "jin-yangqu": {
            "note": (
                "只画阳曲。1945-08-16不是收复文书日，开始日待考，标大致。"
                "周边各县没有逐县名单，不画。"
                "1949-04-24阳曲沦陷，这一天起不再标晋系。"
                "已核對《中華民國史事紀要》民國三十八年一月至六月，印页五二三（PDF 第531页），"
                "页眉四月二十四日，标题共军攻陷山西省太原。写二十二日炮击，二十四日攻入城内。"
                "不把二十二日写成已经入城。不写解放军。"
            ),
            "sources": [V38, WIKI_YAN, ZENODO],
        },
        "jin-recovered": {
            "note": "克复日按已入库的印页。克复之后没有逐日再核，标大致，收到下一份县名单或1945-08-16。",
            "sources": [V27, V28B, ZENODO],
        },
        "ccp-sx": {
            "note": (
                "1949-04-24起按省会日标中国共产党，大致，不是逐县。"
                "阳曲这一天沦陷已核对，见印页五二三。其余县不是逐县入城。"
                "显示写沦陷，不写解放军。"
            ),
            "sources": [V38, ZENODO],
        },
        "gui-hold": {
            "note": (
                "1930-01-01至1949-12-04，落在广西这一块 ENP 省界里的 1931 年治所标桂系，大致，不是逐县核实。"
                "1月1日不是到任日。"
                "1925年统一日没有锁。民国十四年七月至十二月没有县名单，不从1925年把各县涂上。"
                "1924-08-07柳州、10月1日通电、10月9日陆荣廷下野都没有县名单，不从那几天连写到1930。"
                "1927–1929扩到湖南、湖北，没有县名单，湘鄂各县不画。"
                "1929–1930失势与重回的日子没有锁，1930-01-01以前不画。"
                "1936两广事变不把广东、湖南各县划给桂系。"
                "抗战期间邕宁、桂林、马平按已核对的沦陷日从这块填色里挖出。"
            ),
            "sources": [V13, V14, WIKI_GUI, ZENODO],
        },
        "ccp-gx": {
            "note": (
                "1949-12-04起按省会日标中国共产党，大致，不是逐县。"
                "南宁入城这一册没有写成标题，仍未核对。显示写沦陷，不写解放军。"
            ),
            "sources": [V38, "https://www.gxdag.org.cn/show/141/2749", ZENODO],
        },
    }

    for cell in shanxi:
        cid = cell["id"]
        add(spans, cid, **{
            "from": "1917-09-01", "until": "1937-11-12",
            "actual": "晋系（阎锡山）", "certainty": "大致",
            "note": notes["jin-prewar"]["note"], "sources": notes["jin-prewar"]["sources"],
            "priority": 10, "paint": "jin-prewar",
        })
        add(spans, cid, **{
            "from": "1937-11-12", "until": "1945-08-16",
            "actual": "实控待考", "certainty": "待考",
            "note": notes["jin-gap-war"]["note"], "sources": notes["jin-gap-war"]["sources"],
            "priority": 0, "paint": None,
        })
        if cid == "mcgd:s1126":
            add(spans, cid, **{
                "from": "1945-08-16", "until": "1949-04-24",
                "actual": "晋系（阎锡山）", "certainty": "大致",
                "note": notes["jin-yangqu"]["note"], "sources": notes["jin-yangqu"]["sources"],
                "priority": 50, "paint": "jin-yangqu",
            })
        else:
            add(spans, cid, **{
                "from": "1945-08-16", "until": "1949-04-24",
                "actual": "实控待考", "certainty": "待考",
                "note": notes["jin-gap-late"]["note"], "sources": notes["jin-gap-late"]["sources"],
                "priority": 0, "paint": None,
            })
        add(spans, cid, **{
            "from": "1949-04-24", "until": "1950-01-01",
            "actual": "中国共产党", "certainty": "大致",
            "note": notes["ccp-sx"]["note"], "sources": notes["ccp-sx"]["sources"],
            "priority": 10, "paint": None,
        })

    recovered_note = notes["jin-recovered"]["note"]
    for cid, start, _name, page in RECOVERED:
        add(spans, cid, **{
            "from": start, "until": "1945-08-16",
            "actual": "晋系（阎锡山）", "certainty": "大致",
            "note": recovered_note + page,
            "sources": notes["jin-recovered"]["sources"],
            "priority": 25, "paint": None,
        })

    for cell in guangxi:
        cid = cell["id"]
        add(spans, cid, **{
            "from": "1930-01-01", "until": "1949-12-04",
            "actual": "桂系（李宗仁、白崇禧）", "certainty": "大致",
            "note": notes["gui-hold"]["note"], "sources": notes["gui-hold"]["sources"],
            "priority": 10, "paint": "gui",
        })
        add(spans, cid, **{
            "from": "1949-12-04", "until": "1950-01-01",
            "actual": "中国共产党", "certainty": "大致",
            "note": notes["ccp-gx"]["note"], "sources": notes["ccp-gx"]["sources"],
            "priority": 10, "paint": None,
        })

    resolved = {}
    for cid, cell in cells.items():
        rows = resolve(spans[cid])
        resolved[cid] = {**cell, "spans": rows}

    fills = []
    paint_ids = ("jin-prewar", "jin-yangqu", "gui")
    meta = {
        "jin-prewar": ("晋系（阎锡山）", "晋系（阎锡山）", "jin", "jin-prewar"),
        "jin-yangqu": ("晋系（阎锡山）", "晋系（阎锡山，阳曲）", "jin", "jin-yangqu"),
        "gui": ("桂系（李宗仁、白崇禧）", "桂系（李宗仁、白崇禧）", "gui", "gui-hold"),
    }
    for paint in paint_ids:
        actual, name_zh, slug, note_id = meta[paint]
        pieces = []
        for cid, cell in resolved.items():
            for sp in cell["spans"]:
                if sp["paint"] == paint:
                    pieces.append((sp["from"], sp["until"], cid))
        dates = sorted({a for a, _, _ in pieces} | {b for _, b, _ in pieces})
        for a, b in zip(dates, dates[1:]):
            ids = sorted({cid for s, e, cid in pieces if s <= a and b <= e})
            if not ids:
                continue
            if fills and fills[-1]["paint"] == paint and fills[-1]["until"] == a and fills[-1]["counties"] == ids:
                fills[-1]["until"] = b
                continue
            fills.append({
                "id": f"rocfill_{slug}_{a}",
                "paint": paint,
                "slug": slug,
                "actual": actual,
                "name_zh": name_zh,
                "from": a,
                "until": b,
                "counties": ids,
                "certainty": "大致",
                "note": note_id,
            })

    gaps = [
        {
            "id": "jin-1912",
            "certainty": "待考",
            "note": "1912至1917-09-01阎锡山任都督的月日没有锁到日。不把1912-01-01写成到任日，山西各县这一段不画。",
        },
        {
            "id": "jin-1930-outside",
            "certainty": "待考",
            "note": "1930年中原大战前后，晋系在河北、察哈尔、绥远的县界没有名单。不把这三省写成晋系。",
        },
        {
            "id": "gui-1925",
            "certainty": "待考",
            "note": "1925年广西统一日没有锁。民国十四年七月至十二月没有县名单。不从1925年涂各县。",
        },
        {
            "id": "gui-1927-hunan-hubei",
            "certainty": "待考",
            "note": "1927–1929新桂系扩到湖南、湖北。没有逐县名单，湘鄂各县不画，也不用今天的省界。",
        },
        {
            "id": "gui-1929",
            "certainty": "待考",
            "note": "1929年蒋桂战争后失去全省、以及重回广西的日子没有锁。1930-01-01以前广西各县不标新桂系。",
        },
        {
            "id": "gui-1936",
            "certainty": "待考",
            "note": "1936年两广事变不把广东、湖南各县划给桂系。广西各县仍只按1930–1949那一批大致。",
        },
    ]

    by_province = {"shanxi": [], "guangxi": []}
    for cid, cell in resolved.items():
        by_province[cell["province"]].append(cid)
    for key in by_province:
        by_province[key].sort()

    payload = {
        "geom": "MCGD_Rep V2 1931年治所泰森多边形，裁在 ENP-China 省界上。不是今天的县界。",
        "notes": notes,
        "gaps": gaps,
        "fills": fills,
        "by_province": by_province,
        "counties": resolved,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def tally(prov, day):
        from collections import Counter
        c = Counter()
        for cid in by_province[prov]:
            hit = None
            for sp in resolved[cid]["spans"]:
                if sp["from"] <= day < sp["until"]:
                    hit = sp
                    break
            c[(hit["actual"] if hit else "无", hit["certainty"] if hit else "无")] += 1
        return dict(c)

    print(f"shanxi {len(shanxi)} guangxi {len(guangxi)} fills {len(fills)}")
    for day in ("1920-07-01", "1930-06-01", "1937-07-01", "1938-01-01", "1940-06-01", "1946-06-01", "1949-04-24"):
        print(day, "晋", tally("shanxi", day))
    for day in ("1926-07-01", "1930-06-01", "1936-06-01", "1939-12-01", "1944-11-15", "1949-12-03", "1949-12-04"):
        print(day, "桂", tally("guangxi", day))
    for cid, label in (("mcgd:s1126", "阳曲"), ("mcgd:s1086", "大同"), ("mcgd:s1101", "桂林"), ("mcgd:s670", "邕宁"), ("mcgd:s1509", "马平")):
        print("---", label)
        for sp in resolved[cid]["spans"]:
            print(f"  {sp['from']} {sp['until']} {sp['certainty']} {sp['actual']} paint={sp['paint']}")


if __name__ == "__main__":
    main()
