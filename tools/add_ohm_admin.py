"""从 OpenHistoricalMap 追加带起止日期的欧洲一级区划。

OHM 整体是 CC0。关系上另标了非 CC0 许可的不收。
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import polygonize, unary_union

from build_europe_admin import clean_geom, dump_geom

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "geom" / "europe_admin.geojson"
IDS = [
    # 德意志帝国各邦与阿尔萨斯-洛林，1871 年前后
    2690438, 2661269, 2745099, 2661249, 2691485, 2856859, 2831961, 2690945,
    2745098, 2690434, 2692588, 2856512, 2691965, 2959353, 2691495, 2745232,
    2691488, 2745231, 2693575, 2690430, 2690419, 2691491, 2693616, 2691970,
    2747275, 2831960, 2831782, 2692484, 2831781, 2831783, 2692487, 2831780,
    2830675, 2830678, 2692300, 2692486, 2690426,
    # 丹麦 1970–2006 年的县，另加博恩霍尔姆
    2855342, 2855343, 2850339, 2850142, 2849796, 2850021, 2855334, 2855332,
    2849557, 2849983, 2850143, 2850020, 2855344,
    # 奥地利第一共和国时期的州
    2684077, 2928473, 2747803, 2742908, 2746440, 2684073, 2852310,
    # 比利时省，1815–1940
    2945090, 2945092, 2945081, 2945074, 2945094, 2951908, 2945066, 2945065,
    2945069, 2884612, 2945110, 2951914,
]
ZH = {
    "Königreich Bayern": "巴伐利亚", "Württemberg": "符腾堡", "Baden": "巴登",
    "Königreich Sachsen": "萨克森", "Elsaß-Lothringen": "阿尔萨斯-洛林", "Hessen": "黑森",
    "Großherzogtum Mecklenburg-Schwerin": "梅克伦堡-什未林",
    "Großherzogtum Mecklenburg-Strelitz": "梅克伦堡-施特雷利茨",
    "Oldenburg": "奥尔登堡", "Braunschweig": "不伦瑞克", "Herzogtum Anhalt": "安哈尔特",
    "Fürstentum Lippe": "利珀", "Schaumburg-Lippe": "绍姆堡-利珀", "Bremen": "不来梅",
    "Freie und Hansestadt Hamburg": "汉堡", "Freie und Hansestadt Lübeck": "吕贝克",
    "Sachsen-Coburg und Gotha": "萨克森-科堡-哥达", "Sachsen-Altenburg": "萨克森-阿尔滕堡",
    "Sachsen-Meiningen": "萨克森-迈宁根", "Sachsen-Weimar-Eisenach": "萨克森-魏玛-艾森纳赫",
    "Fürstentum Schwarzburg-Rudolstadt": "施瓦茨堡-鲁多尔施塔特",
    "Fürstentum Schwarzburg-Sondershausen": "施瓦茨堡-松德斯豪森",
    "Fürstentum Reuß jüngerer Linie": "罗伊斯幼支", "Fürstentum Reuß älterer Linie": "罗伊斯长支",
    "Waldeck-Pyrmont": "瓦尔德克-皮尔蒙特",
    "Frederiksborg Amt": "腓特烈堡", "Københavns Amt": "哥本哈根", "Fyns Amt": "菲英",
    "Nordjyllands Amt": "北日德兰", "Ribe Amt": "里伯", "Ringkjøbing Amt": "灵克宾",
    "Roskilde Amt": "罗斯基勒", "Storstrøms Amt": "斯托海峡", "Sønderjyllands Amt": "南日德兰",
    "Vejle Amt": "瓦埃勒", "Viborg Amt": "维堡", "Århus Amt": "奥胡斯", "Bornholms Amt": "博恩霍尔姆",
    "Niederösterreich": "下奥地利", "Oberösterreich": "上奥地利", "Burgenland": "布尔根兰",
    "Steiermark": "施蒂利亚", "Tirol": "蒂罗尔", "Vorarlberg": "福拉尔贝格", "Salzburg": "萨尔茨堡",
    "Antwerpen": "安特卫普", "Brabant": "布拉班特", "Hainaut": "埃诺", "Limburg": "林堡",
    "Luxembourg": "卢森堡", "Oost-Vlaanderen": "东佛兰德", "West-Vlaanderen": "西佛兰德",
    "Liège": "列日", "Namur": "那慕尔",
}
NOTE = (
    "OpenHistoricalMap 关系，数据库为 CC0。关系上另标了非 CC0 许可的没有收。"
    "只有年份的，从该年1月1日画到次年1月1日，不是1月1日发生了变化。"
    "https://www.openhistoricalmap.org/"
)
KIND = {
    "de": "邦", "dk": "县", "at": "州", "be": "省",
}


def next_day(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return (date(y, m, d) + timedelta(days=1)).isoformat()


def as_span(start: str, end: str) -> tuple[str, str] | None:
    def one(value: str, ending: bool) -> str | None:
        value = (value or "").strip()
        if len(value) == 4 and value.isdigit():
            year = int(value) + (1 if ending else 0)
            return f"{year:04d}-01-01"
        if len(value) == 7:
            year, month = (int(x) for x in value.split("-"))
            if ending:
                month += 1
                if month == 13:
                    year, month = year + 1, 1
            return f"{year:04d}-{month:02d}-01"
        if len(value) == 10:
            return next_day(value) if ending else value
        return None

    a, b = one(start, False), one(end, True)
    if not a or not b or not a < b:
        return None
    return a, b


def polygon_of(element):
    lines = []
    for member in element.get("members") or []:
        if member.get("type") != "way" or not member.get("geometry"):
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in member["geometry"]]
        if len(coords) >= 2:
            lines.append(LineString(coords))
    if not lines:
        return None
    parts = [poly for poly in polygonize(lines) if poly.area > 0.002]
    if not parts:
        return None
    return unary_union(parts)


def fetch(ids):
    query = f"[out:json][timeout:120];relation(id:{','.join(str(i) for i in ids)});out geom;"
    req = urllib.request.Request(
        "https://overpass-api.openhistoricalmap.org/api/interpreter",
        data=query.encode(), headers={"User-Agent": "world-history-atlas/research"},
    )
    with urllib.request.urlopen(req, timeout=150) as response:
        return json.load(response)["elements"]


def group(name: str) -> str:
    if name.endswith("Amt"):
        return "dk"
    if name in {"Niederösterreich", "Oberösterreich", "Burgenland", "Steiermark", "Tirol", "Vorarlberg", "Salzburg"}:
        return "at"
    if name in {"Antwerpen", "Brabant", "Hainaut", "Limburg", "Luxembourg", "Oost-Vlaanderen", "West-Vlaanderen", "Liège", "Namur"}:
        return "be"
    return "de"


def main():
    data = json.loads(OUT.read_text(encoding="utf-8"))
    features = [feat for feat in data["features"] if feat["properties"].get("source_id") != "ohm"]
    elements = fetch(IDS)
    skipped = []
    for element in elements:
        tags = element.get("tags") or {}
        lic = (tags.get("license") or tags.get("licence") or "").lower()
        if lic and "cc0" not in lic:
            skipped.append((element["id"], tags.get("name"), lic))
            continue
        name = tags.get("name") or ""
        span = as_span(tags.get("start_date") or "", tags.get("end_date") or "")
        geom = clean_geom(polygon_of(element), 0.02) if span else None
        if geom is None or name not in ZH:
            skipped.append((element["id"], name, "no-geom" if span else "date"))
            continue
        which = group(name)
        nominal = {"de": "德意志", "dk": "丹麦", "at": "奥地利", "be": "比利时"}[which]
        start, end = span
        # 1922-01-01 起维也纳单独建州。这份下奥地利把维也纳包在里面，此后不用。
        if element["id"] == 2684077:
            end = min(end, "1922-01-01")
        if not start < end:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"ohm-{element['id']}",
                "name_src": name,
                "name": ZH[name],
                "kind": KIND[which],
                "nominal": nominal,
                "from": start,
                "until": end,
                "source_id": "ohm",
                "license": "CC0",
                "url": f"https://www.openhistoricalmap.org/relation/{element['id']}",
                "precision": NOTE,
            },
            "geometry": dump_geom(geom),
        })
    data["features"] = features
    gaps = [item for item in data.get("gaps") or [] if "OpenHistoricalMap" not in item]
    gaps.append(
        "OpenHistoricalMap（CC0）补了 1871–1918 年有关系的德意志各邦和阿尔萨斯-洛林、"
        "1839 年前后至 1940 年的比利时省、1970–2006 年的丹麦县，以及 1920 年前后至 1938 年的部分奥地利州。"
        "关系上标了非 CC0 许可的没有收。荷兰、挪威、葡萄牙、匈牙利王国的州、南斯拉夫和罗马尼亚仍待考。"
        "维也纳没有单独的州关系。"
    )
    data["gaps"] = gaps
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("features", len(features), "skipped", len(skipped))
    for row in skipped[:20]:
        print(" skip", row)
    units = [(json.loads(json.dumps(feat["geometry"])), feat["properties"]) for feat in features if feat["properties"]["source_id"] == "ohm"]
    from shapely.geometry import shape
    units = [(shape(geom), prop) for geom, prop in units]
    checks = [
        ("1910-06-01", 11.575, 48.137, "巴伐利亚"),
        ("1910-06-01", 9.182, 48.775, "符腾堡"),
        ("1910-06-01", 8.404, 49.007, "巴登"),
        ("1910-06-01", 13.738, 51.051, "萨克森"),
        ("1910-06-01", 7.752, 48.573, "阿尔萨斯-洛林"),
        ("1872-06-01", 6.175, 49.119, "阿尔萨斯-洛林"),
        ("1980-06-01", 12.568, 55.676, "哥本哈根"),
        ("1925-06-01", 16.373, 48.208, "下奥地利"),
        ("1900-06-01", 4.3517, 50.846, "布拉班特"),
    ]
    for day, lon, lat, expect in checks:
        point = Point(lon, lat)
        hits = []
        for geom, prop in units:
            if prop["from"] <= day < prop["until"] and geom.covers(point):
                hits.append((geom.area, prop["name"]))
        hits.sort()
        got = hits[0][1] if hits else None
        print(("OK" if got == expect else "DIFF"), day, expect, got, hits[:3])


if __name__ == "__main__":
    main()
