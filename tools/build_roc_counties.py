#!/usr/bin/env python3
"""把关内手绘占领框换成 1931 年治所的泰森多边形。

治所：MCGD_Rep V2（Zenodo 5721459，CC BY 4.0，Christian Henriot / ENP-China）。
每个县域是该治所的 Voronoi 单元，再裁到 ENP-China 历史省多边形上。
省多边形的外缘就是这套图的海岸。没有使用 CHGIS。

用法：python3 tools/build_roc_counties.py
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

from shapely.geometry import MultiPoint, Point, mapping, shape
from shapely.ops import voronoi_diagram
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.build_control_zones import resolve  # noqa: E402

CSV_SRC = Path("/tmp/wha-mcgd/MCGD_Rep_V2.csv")
CSV_DST = ROOT / "data" / "curated" / "geom" / "MCGD_Rep_V2.csv"
CELLS = ROOT / "data" / "curated" / "geom" / "roc_county_cells.geojson"
EXTENTS = ROOT / "data" / "curated" / "geom" / "roc_cell_extents.json"
ZONES = ROOT / "data" / "curated" / "control_zones.json"
BEIYANG = ROOT / "data" / "curated" / "roc_beiyang.json"
GEOM = ROOT / "data" / "curated" / "roc_admin_geom.json"
PHRASE = "大致。县域为治所泰森多边形近似。"

# 1933 年非武装区两专区的 22 县。冀东防共自治政府辖这 22 县。
# https://zh.wikipedia.org/wiki/冀东防共自治政府
EAST_HEBEI = [
    "盧龍", "遷安", "撫寧", "昌黎", "灤縣", "樂亭", "臨榆", "豐潤", "寧河",
    "通縣", "三河", "寶坻", "薊縣", "香河", "昌平", "順義", "密雲", "懷柔", "平谷", "遵化", "興隆", "玉田",
]
# 1934 年 9 月记载里剩下的八个县城。
SOVIET = ["瑞金", "會昌", "雩都", "興國", "寧都", "石城", "寧化", "長汀"]
# 占领层不得早于这些点。坐标与 tools/accept/occupation_fall.py 相同。
CITIES = [
    ("上海", 121.477, 31.233, "1937-11-12"),
    ("南京", 118.8, 32.06, "1937-12-13"),
    ("太原", 112.587, 37.839, "1937-11-08"),
    ("徐州", 117.257, 34.302, "1938-05-19"),
    ("武汉", 114.3, 30.59, "1938-10-25"),
    ("广州", 113.264, 23.122, "1938-10-21"),
    ("长沙", 112.971, 28.197, "1944-06-18"),
    ("桂林", 110.29, 25.27, "1944-11-09"),
    ("杭州", 120.169, 30.294, "1937-12-24"),
    ("苏州", 120.614, 31.318, "1937-11-19"),
    ("青岛", 120.038, 36.274, "1938-01-10"),
    ("厦门", 118.077, 24.460, "1938-05-13"),
    ("无锡", 120.291, 31.583, "1937-11-25"),
    ("常州", 119.943, 31.765, "1937-11-29"),
    ("芜湖", 118.370, 31.342, "1937-12-10"),
    ("济南", 116.998, 36.690, "1937-12-27"),
    ("天津", 117.18956, 39.13578, "1937-07-30"),
    ("大同", 113.26351, 40.12123, "1937-09-13"),
    ("保定", 115.51165, 38.85469, "1937-09-22"),
    ("正定", 114.55591, 38.13882, "1937-10-08"),
    ("永城", 116.32010, 33.99361, "1938-05-12"),
    ("宿县", 117.04466, 33.66279, "1938-05-18"),
    ("萧县", 117.02297, 34.21105, "1938-05-18"),
    ("晋城", 112.92418, 35.51057, "1938-06-30"),
    ("阳城", 112.49422, 35.50255, "1938-07-04"),
    ("湖口", 116.29278, 29.72863, "1938-07-05"),
    ("沁水", 112.23888, 35.74570, "1938-07-07"),
    ("翼城", 111.75926, 35.76267, "1938-07-11"),
    ("太湖", 116.33004, 30.37366, "1938-07-26"),
    ("宿松", 116.16988, 30.10481, "1938-08-01"),
    ("黄梅", 115.97605, 30.02688, "1938-08-02"),
    ("瑞昌", 115.76351, 29.63126, "1938-08-24"),
    ("六安", 116.54516, 31.79172, "1938-08-28"),
    ("霍山", 116.40827, 31.38458, "1938-08-29"),
    ("广济", 115.64501, 30.08519, "1938-09-06"),
    ("黄陂", 114.4123, 30.8925, "1938-10-24"),
    ("通山", 114.4833, 29.6345, "1938-11-04"),
    ("崇阳", 114.0420, 29.5768, "1938-11-06"),
    ("固始", 115.72627, 32.23284, "1938-09-06"),
    ("罗山", 114.53985, 32.19885, "1938-09-21"),
    ("鄂城", 114.89211, 30.37975, "1938-10-22"),
    ("通城", 113.89613, 29.28175, "1938-11-09"),
    ("开封", 114.345, 34.802, "1938-06-06"),
    # 治所点。九江、镇江的单元格在更晚的色块里，从沦陷日起补到那一块。
    ("九江", 116.04059, 29.71584, "1938-07-26"),
    ("镇江", 119.45471, 32.19607, "1937-12-08"),
    # 1944 豫中、长衡。坐标是 1931 年治所。已在更晚的大块里，从沦陷日起补到那一块。
    ("郑州", 113.66959, 34.74548, "1944-04-23"),
    ("密县", 113.25948, 34.49820, "1944-04-23"),
    ("许昌", 113.86186, 34.03365, "1944-05-01"),
    ("临颍", 113.97625, 33.80601, "1944-05-02"),
    ("襄城", 113.47119, 33.84313, "1944-05-03"),
    ("临汝", 112.75329, 34.19136, "1944-05-04"),
    ("宜阳", 112.15466, 34.61718, "1944-05-14"),
    ("洛宁", 111.62693, 34.34830, "1944-05-17"),
    ("湘阴", 112.94096, 28.67869, "1944-06-06"),
    ("零陵", 111.53675, 26.26037, "1944-09-06"),
    ("荔浦", 110.24474, 24.43743, "1944-11-03"),
    ("阳朔", 110.29616, 24.69926, "1944-11-03"),
]
# 从沦陷日起另画、并且要写明收到哪一天的单元格。until 为空则收到下一块盖住这里的日期；没有下一块就收到 1945-08-16。
# 汕头市区落在 1931 年朝阳治所的单元格里。澄海治所也在原来的汕头方框里，两格同一天，不把 3 月 27 日写成已经沦陷。
JP = {"qid": "Q188712", "zh": "大日本帝国"}
WANG = {"qid": "Q696242", "zh": "汪精卫政权"}
REFORM = {"qid": "Q708865", "zh": "中华民国维新政府"}
GROWTH = [
    ("安庆", [(117.037, 30.53782)], "1938-06-13", "1940-03-30", REFORM, "中华民国维新政府（安庆）",
     "怀宁县域。1938-06-13 城垣陷落。6 月 6 日的色块更早，从那一块移出。1940-03-30 起改记汪精卫政权。"),
    ("安庆", [(117.037, 30.53782)], "1940-03-30", "1945-08-16", WANG, "汪精卫政权（安庆）",
     "怀宁县域。1940-03-30 起随华中日占区改记汪精卫政权，收到 1945-08-16。"),
    ("宜昌", [(111.28472, 30.70323)], "1940-06-12", "1945-08-16", WANG, "汪精卫政权（宜昌）",
     "宜昌县域。1940-06-12 沦陷。印页六九一（PDF 第698页）页眉六月十二日，写空军在重庆上空击落日本飞机，没有宜昌。印页七〇五（PDF 第711页）页眉六月十七日，写街市已经放弃，没有写出是哪一天。原来的手绘范围没有盖住这个治所，不把邻近县加进来。"),
    ("海口", [(110.19939, 20.05511)], "1939-02-10", "1940-03-30", JP, "日军占领区（海口）",
     "海口治所的单元格。1939-02-10 起。琼山和岛上其余县仍从 1939-03-27 的海南块起，不提前。"),
    ("海口", [(110.19939, 20.05511)], "1940-03-30", "1945-08-16", WANG, "汪精卫政权（海口）",
     "海口治所的单元格。1940-03-30 起与海南岛其余占领层一样改记汪精卫政权。"),
    ("汕头", [(116.682, 23.354), (116.72577, 23.48103)], "1939-06-21", "1940-03-30", JP, "日军占领区（汕头）",
     "汕头市区落在 1931 年朝阳治所的单元格里，澄海治所也在原来的汕头方框里。两格从 1939-06-21 起，不再从 3 月 27 日起。潮安不在这框里。"),
    ("南宁", [(108.29251, 22.80864)], "1939-11-24", "1940-10-29", JP, "日军军事占领区（南宁）",
     "邕宁县域。1939-11-24 沦陷。1940-10-28 晚放弃，29 日收复，收到 10 月 29 日。1944 年 11 月的第二次占领不在这一格里。"),
    ("连江", [(119.51695, 26.20239)], "1941-04-19", "1941-09-03", JP, "日军军事占领区（连江）",
     "连江县域。1941-04-19 下午陷落，收到福州这一格的 1941-09-03。结束日待考。"),
    ("长乐", [(119.56204, 25.94428)], "1941-04-19", "1941-09-03", JP, "日军军事占领区（长乐）",
     "长乐县域。1941-04-19 下午陷落，收到福州这一格的 1941-09-03。结束日待考。"),
    ("惠阳", [(114.4232, 23.0846)], "1938-10-15", "1938-11-12", JP, "日军占领区（惠阳）",
     "惠阳县域。1938-10-15 失守，1938-11-12 克复。不在既有大块里，收到克复日。"),
    ("福州", [(119.32158, 26.07395), (119.32122, 26.09425)], "1941-04-22", "1941-09-03", JP, "日军军事占领区（福州）",
     "福州和闽侯两个治所几乎叠在一起，两格都画。1941-04-22 午后国军退出，9 月 3 日撤出。连江、长乐、福清、平潭没有并进来。"),
    ("福州", [(119.32158, 26.07395), (119.32122, 26.09425)], "1944-10-04", "1945-05-18", JP, "日军军事占领区（福州）",
     "福州、闽侯两格。1944-10-04 再沦陷，1945-05-18 光复，这一天起不再画。PDF 第1至383页按列扫过，没有认出福州、闽侯、闽海、长乐、连江或福清。"),
    ("衡阳", [(112.56975, 26.93801)], "1944-08-08", "1945-08-16", WANG, "汪精卫政权（衡阳）",
     "衡阳县域。1944-08-08 沦陷。原来的湖南手绘范围没有盖住这个治所。"),
    ("柳州", [(109.26731, 24.30179)], "1944-11-11", "1945-06-29", JP, "日军军事占领区（柳州）",
     "1931 年治所仍名马平。1944-11-11 沦陷。桂柳走廊的手绘范围没有盖住这个治所，控制方沿用那一条的日军军事占领，不是汪政权。"),
]
SEA = [(122.8, 31.0), (122.6, 36.3), (120.2, 26.2), (113.8, 21.6)]
SNAP = 0.03
# MCGD 的省名和 ENP 的省名不是同一套字。只在点落在那块省界里、或离它不到 SNAP 度时才用。
PREF = {
    "遼寧": "奉天", "遼北": "奉天", "遼西": "奉天", "西康": "川邊", "海南": "廣東",
    "武漢": "湖北", "重慶市": "四川", "內蒙古": "綏遠", "松江": "吉林", "合江": "吉林", "興安": "黑龍江",
}
V33_46 = "https://www.drnh.gov.tw/p/404-1003-13336.php?Lang=zh-tw"
V33_79 = "https://www.drnh.gov.tw/p/404-1003-13338.php?Lang=zh-tw"
V33_1012 = "https://www.drnh.gov.tw/p/404-1003-13334.php?Lang=zh-tw"
V34_57 = "https://www.drnh.gov.tw/p/404-1003-13342.php?Lang=zh-tw"
ZENODO = "https://zenodo.org/records/5721459"
# 键是 CITIES 里的简体县名。这些县已经在 1944 年的大块里，格子只补到下一块。
CHRONICLE_1944 = {
    "郑州": {
        "name_zh": "华北政务委员会（郑州）",
        "note": (
            "郑县县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页一九九（PDF 第207页），页眉四月二十三日，"
            "写固守郑州之暂编第一旅于本（二十三）日二时奉令突围转进，日军遂陷郑州。"
            "同页写本月二十日向郑州展开攻势，不把二十日写成已经陷落。"
            "1944-08-08 起并入下一块。"
        ),
        "dates": "郑州 1944-04-23 起，收到 1944-08-08。已核對印页一九九。",
        "sources": [V33_46, ZENODO],
    },
    "密县": {
        "name_zh": "华北政务委员会（密县）",
        "note": (
            "密县县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页一九九（PDF 第207页），页眉四月二十三日，"
            "标题写日军侵占郑州、密县。正文写至本日进攻密县外围，战至九时许第二十三师突围。"
            "1944-08-08 起并入下一块。"
        ),
        "dates": "密县 1944-04-23 起，收到 1944-08-08。已核對印页一九九。",
        "sources": [V33_46, ZENODO],
    },
    "许昌": {
        "name_zh": "汪精卫政权（许昌）",
        "note": (
            "许昌县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页二六〇（PDF 第268页），页眉五月一日，标题许昌陷落，"
            "写日军本日先轰炸，再以战车与步兵突入城内，许昌随之陷落。"
            "1944-08-08 起并入下一块。"
        ),
        "dates": "许昌 1944-05-01 起，收到 1944-08-08。已核對印页二六〇。",
        "sources": [V33_46, ZENODO],
    },
    "临颍": {
        "name_zh": "汪精卫政权（临颍）",
        "note": (
            "临颍县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页二九六（PDF 第304页），页眉五月五日，追述攻陷许昌之后二日继陷临颍。"
            "许昌陷落是五月一日。1944-08-08 起并入下一块。"
        ),
        "dates": "临颍 1944-05-02 起，收到 1944-08-08。追述，已核對印页二九六。",
        "sources": [V33_46, ZENODO],
    },
    "襄城": {
        "name_zh": "汪精卫政权（襄城）",
        "note": (
            "襄城县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页二九六（PDF 第304页），页眉五月五日，追述三日再陷襄城。"
            "同页写猛攻郏县，不把郏县写成已经陷落。1944-08-08 起并入下一块。"
        ),
        "dates": "襄城 1944-05-03 起，收到 1944-08-08。追述，已核對印页二九六。",
        "sources": [V33_46, ZENODO],
    },
    "临汝": {
        "name_zh": "汪精卫政权（临汝）",
        "note": (
            "临汝县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页二九六（PDF 第304页），页眉五月五日，追述四日陷临汝。"
            "同页写分股向宝丰、临汝突进，宝丰没有写陷。1944-08-08 起并入下一块。"
        ),
        "dates": "临汝 1944-05-04 起，收到 1944-08-08。追述，已核對印页二九六。",
        "sources": [V33_46, ZENODO],
    },
    "宜阳": {
        "name_zh": "华北政务委员会（宜阳）",
        "note": (
            "宜阳县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页四三〇（PDF 第438页），页眉五月二十一日，追述本月十四日陷宜阳。"
            "同页十六日陷韩城，韩城对不上一九三一年河南的县，不画。"
            "1944-08-08 起并入下一块。"
        ),
        "dates": "宜阳 1944-05-14 起，收到 1944-08-08。追述，已核對印页四三〇。",
        "sources": [V33_46, ZENODO],
    },
    "洛宁": {
        "name_zh": "华北政务委员会（洛宁）",
        "note": (
            "洛宁县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页四三〇（PDF 第438页），页眉五月二十一日，追述本月十七日陷洛宁。"
            "同页十八日陷陕县、二十日攻入卢氏。陕县不在既有大块里，卢氏没有一九三一年治所，都不画。"
            "1944-08-08 起并入下一块。"
        ),
        "dates": "洛宁 1944-05-17 起，收到 1944-08-08。追述，已核對印页四三〇。",
        "sources": [V33_46, ZENODO],
    },
    "湘阴": {
        "name_zh": "汪精卫政权（湘阴）",
        "note": (
            "湘阴县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
            "印页六四六（PDF 第653页），页眉六月六日，标题日军分陷湘阴、益阳、古港等地，"
            "正文写迄本（六）日一部陷芦林潭、湘阴。"
            "益阳正文写分犯，不把标题的分陷写成已经陷落。芦林潭、古港不是县。"
            "1944-08-08 起并入下一块。"
        ),
        "dates": "湘阴 1944-06-06 起，收到 1944-08-08。已核對印页六四六。",
        "sources": [V33_46, ZENODO],
    },
    "零陵": {
        "name_zh": "日军军事占领区（零陵）",
        "note": (
            "零陵县域。已核對《中華民國史事紀要》民國三十三年七月至九月，"
            "印页六六四（PDF 第672页），页眉九月七日，标题湖南零陵失陷。"
            "正文写至九月六日乘夜攻入零陵，本（七）日各军突围，王甲本力战殉国。"
            "攻入是六日。1944-11-10 起并入桂柳走廊。"
        ),
        "dates": "零陵 1944-09-06 起，收到 1944-11-10。已核對印页六六四。",
        "sources": [V33_79, ZENODO],
    },
    "荔浦": {
        "name_zh": "日军军事占领区（荔浦）",
        "note": (
            "荔浦县域。已核對《中華民國史事紀要》民國三十三年十月至十二月，"
            "印页三七五（PDF 第383页），页眉十一月九日。"
            "桂林本日为日军突入，这一天不改。同页追述本月三日第三师攻陷荔浦。"
            "1944-11-10 起并入桂柳走廊。"
        ),
        "dates": "荔浦 1944-11-03 起，收到 1944-11-10。追述，已核對印页三七五。",
        "sources": [V33_1012, ZENODO],
    },
    "阳朔": {
        "name_zh": "日军军事占领区（阳朔）",
        "note": (
            "阳朔县域。已核對《中華民國史事紀要》民國三十三年十月至十二月，"
            "印页三七五（PDF 第383页），页眉十一月九日，追述本月三日第十三师团进占阳朔。"
            "桂林仍是十一月九日。1944-11-10 起并入桂柳走廊。"
        ),
        "dates": "阳朔 1944-11-03 起，收到 1944-11-10。追述，已核對印页三七五。",
        "sources": [V33_1012, ZENODO],
    },
}


def load_seats():
    if not CSV_DST.exists():
        if not CSV_SRC.exists():
            raise SystemExit("missing MCGD csv")
        CSV_DST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CSV_SRC, CSV_DST)
    rows = list(csv.DictReader(CSV_DST.open(encoding="utf-8-sig")))
    seats = []
    used = set()
    for i, r in enumerate(rows):
        try:
            lon, lat = float(r["LONG"]), float(r["LAT"])
        except ValueError:
            continue
        fid = (r.get("FID") or "").strip()
        loc = (r.get("LocID") or "").strip()
        if fid and fid not in ("NA", "None"):
            cid = "mcgd:" + fid
        elif loc and loc not in ("NA", "None"):
            cid = "mcgd:" + loc
        else:
            cid = f"mcgd:{r['Name_ZhT']}-{i}"
        n = cid
        k = 2
        while n in used:
            n = f"{cid}-{k}"
            k += 1
        used.add(n)
        seats.append({
            "id": n,
            "name": r["Name_ZhT"],
            "province": r["Province_ZhT"],
            "level": r["Level"],
            "lon": lon,
            "lat": lat,
        })
    return seats


def load_provinces():
    units = json.loads(GEOM.read_text(encoding="utf-8"))["units"]
    geoms = []
    for u in units:
        if str(u["sid"]).startswith("1947-") and u["sid"] != "1947-台灣":
            continue
        g = make_valid(shape(u["geom"]))
        if g.is_empty:
            continue
        geoms.append((u["sid"], u["name_1912"], g))
    return geoms


def build_cells(seats, provinces):
    polys = [g for _, _, g in provinces]
    by_pname = {}
    for _sid, name, g in provinces:
        by_pname.setdefault(name, g)
    tree = STRtree(polys)
    points = []
    kept = []
    outside = []
    for s in seats:
        pt = Point(s["lon"], s["lat"])
        containers = []
        for i in tree.query(pt):
            g = polys[int(i)]
            if g.covers(pt):
                containers.append(provinces[int(i)])
        pref_name = PREF.get(s["province"], s["province"])
        pref = by_pname.get(pref_name)
        clip = None
        pname = None
        if pref is not None and pref.covers(pt):
            pname, clip = pref_name, pref
        elif containers:
            _sid, pname, clip = min(containers, key=lambda t: t[2].area)
        elif pref is not None and pref.distance(pt) <= SNAP:
            pname, clip = pref_name, pref.buffer(SNAP)
        else:
            nearest = min(provinces, key=lambda t: t[2].distance(pt))
            if nearest[2].distance(pt) <= SNAP:
                pname, clip = nearest[1], nearest[2].buffer(SNAP)
        if clip is None:
            outside.append(s["name"] + "/" + s["province"])
            continue
        s = dict(s)
        s["pname"] = pname
        s["prov"] = clip
        kept.append(s)
        points.append(pt)
    print("outside ENP", len(outside), " ".join(outside[:30]))
    regions = voronoi_diagram(MultiPoint(points), tolerance=0)
    geoms = list(regions.geoms)
    rtree = STRtree(geoms)
    features = []
    missed = 0
    for s in kept:
        pt = Point(s["lon"], s["lat"])
        cell = None
        for i in rtree.query(pt):
            g = geoms[int(i)]
            if g.covers(pt):
                cell = g
                break
        if cell is None:
            missed += 1
            continue
        clipped = make_valid(cell.intersection(s["prov"]))
        if clipped.is_empty or clipped.area < 1e-8:
            missed += 1
            continue
        clipped = clipped.simplify(0.001, preserve_topology=True)
        features.append({
            "type": "Feature",
            "properties": {
                "id": s["id"],
                "name": s["name"],
                "province": s["pname"],
                "level": s["level"],
                "lon": round(s["lon"], 5),
                "lat": round(s["lat"], 5),
            },
            "geometry": mapping(clipped),
        })
    print(f"seats {len(seats)} inside ENP {len(kept)} cells {len(features)} missed {missed}")
    return features


def by_name(features, names, province=None):
    found = {}
    for f in features:
        n = f["properties"]["name"]
        if n not in names:
            continue
        if province and f["properties"]["province"] != province and n in found:
            continue
        if n in found and province and f["properties"]["province"] == province:
            found[n] = f
            continue
        if n not in found:
            found[n] = f
    missing = [n for n in names if n not in found]
    if missing:
        raise SystemExit("county names missing: " + "、".join(missing))
    return [found[n]["properties"]["id"] for n in names]


def spec_blob(spec):
    return json.dumps(spec, ensure_ascii=False)


def should_convert(zone):
    if not str(zone.get("id", "")).startswith("sjw_"):
        return False
    if zone["id"] in ("sjw_manchuria_1931",) or "unverified" in zone["id"] or zone["id"].startswith("sjw_cell_"):
        return False
    blob = spec_blob(zone.get("geometry") or {})
    if "basemap" in blob or "cshapes" in blob:
        return False
    if "polygon" in blob or "roc_counties" in blob:
        return True
    return False


def cell_at(features, prepared, lon, lat):
    pt = Point(lon, lat)
    for i in prepared.query(pt):
        if features[int(i)]["geom"].covers(pt):
            return features[int(i)]["properties"]["id"]
    return None


def main():
    seats = load_seats()
    provinces = load_provinces()
    features = build_cells(seats, provinces)
    fc = {
        "type": "FeatureCollection",
        "source": {
            "seats": "MCGD_Rep V2",
            "url": "https://zenodo.org/records/5721459",
            "license": "CC BY 4.0",
            "attribution": "Christian Henriot, ENP-China. Modern China Geospatial Database, Republican China Dataset.",
            "clip": "ENP-China / Virtual Shanghai historical provinces (CC0). The province outline supplies the coastline.",
            "note": "县域为治所泰森多边形近似，不是县界，也不是 CHGIS。",
        },
        "features": features,
    }
    CELLS.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", CELLS, "bytes", CELLS.stat().st_size)

    geoms = []
    for f in features:
        g = make_valid(shape(f["geometry"]))
        f["geom"] = g
        geoms.append(g)
    tree = STRtree(geoms)
    sea_hits = []
    for lon, lat in SEA:
        cid = cell_at(features, tree, lon, lat)
        if cid:
            sea_hits.append((lon, lat, cid))
    print("sea hits", sea_hits)

    doc = json.loads(ZONES.read_text(encoding="utf-8"))
    doc["zones"] = [z for z in doc["zones"] if not str(z.get("id", "")).startswith("sjw_cell_")]
    extents = json.loads(EXTENTS.read_text(encoding="utf-8")) if EXTENTS.exists() else {}
    id_of = {f["properties"]["id"]: f for f in features}
    seat_pt = {f["properties"]["id"]: Point(f["properties"]["lon"], f["properties"]["lat"]) for f in features}

    converted = []
    for zone in doc["zones"]:
        if not should_convert(zone):
            continue
        if zone["id"] not in extents:
            if "polygon" not in spec_blob(zone.get("geometry") or {}):
                continue
            extents[zone["id"]] = zone["geometry"]
        extent = resolve(extents[zone["id"]])
        ids = []
        if zone["id"] == "sjw_east_hebei":
            ids = by_name(features, EAST_HEBEI, province="河北")
        else:
            for fid, pt in seat_pt.items():
                if extent.covers(pt):
                    ids.append(fid)
            for _name, lon, lat, _fall in CITIES:
                if extent.covers(Point(lon, lat)):
                    cid = cell_at(features, tree, lon, lat)
                    if cid and cid not in ids:
                        ids.append(cid)
        ids = sorted(set(ids))
        if not ids:
            print("EMPTY", zone["id"])
            continue
        zone["geometry"] = {"roc_counties": ids}
        note = zone.get("note") or ""
        if "泰森" not in note:
            zone["note"] = (note + " " + PHRASE).strip()
        converted.append(zone)
        print(f"{zone['id']:40} counties={len(ids):4}")

    # 城池点若落在更早的块里，从那一块拿掉，并补上从沦陷日起的县域。
    by_id = {z["id"]: z for z in converted}
    supplements = []
    for name, lon, lat, fall in CITIES:
        cid = cell_at(features, tree, lon, lat)
        if not cid:
            print("NO CELL", name)
            continue
        offenders = []
        for z in converted:
            if cid in z["geometry"]["roc_counties"] and (z.get("from") or "") < fall:
                offenders.append(z)
        for z in offenders:
            z["geometry"]["roc_counties"] = [i for i in z["geometry"]["roc_counties"] if i != cid]
        starters = [z for z in converted if cid in z["geometry"]["roc_counties"] and (z.get("from") or "") >= fall]
        if starters and min(z["from"] for z in starters) <= fall:
            continue
        gap_until = min((z["from"] for z in starters), default=None)
        if gap_until is None:
            if not offenders:
                print("UNCOVERED", name, cid)
                continue
            gap_until = max(z.get("until") or "1945-08-16" for z in offenders)
        src = offenders[0] if offenders else starters[0]
        sid = f"sjw_cell_{cid}_{fall}_{name}"
        if any(z["id"] == sid for z in doc["zones"]):
            continue
        supplements.append({
            "id": sid,
            "group": "sino_japanese_war",
            "kind": "occupied",
            "as_polity": True,
            "name_zh": src["name_zh"],
            "name_en": src.get("name_en") or src["name_zh"],
            "controller": src["controller"],
            "from": fall,
            "until": gap_until,
            "geometry": {"roc_counties": [cid]},
            "approx": True,
            "note": f"{name}县域。{PHRASE}不把沦陷日之前的色块扩到这个治所。未核对《中華民國史事紀要》。",
            "dates_note": f"{name} {fall} 起，收到下一块盖住这里的日期。",
            "sources": src.get("sources") or [],
        })
        print("supplement", name, fall, gap_until, cid)
    for s in supplements:
        if s["id"].endswith("_徐州"):
            s["note"] = (
                "徐州县域。已核對《中華民國史事紀要》民國二十七年一月至六月，"
                "印页四七九（PDF 第483页），页眉民国二十七年五月十八、十九日，写至十时徐州失守。"
                "6月6日起并入后面那一块。" + PHRASE
            )
            s["dates_note"] = "徐州 1938-05-19 起，收到 1938-06-06。已核對《中華民國史事紀要》印页四七九。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13313.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_镇江"):
            s["note"] = (
                "镇江县域。江苏省志大事年表写1937年12月8日镇江、靖江失陷。"
                "12月6日天谷支队的说法没有并成这一天。"
                "《中華民國史事紀要》民國二十六年七月至十二月，印页七一二（PDF 第720页），"
                "页眉十二月五、六日，是国府会议和任命，没有镇江。"
                "印页七二〇（PDF 第728页），页眉十二月八、九日，写日军进犯南京外围，板桥、牛首山、淳化、汤水、龙潭失守，没有镇江城。"
                "PDF 第620–800页没有认出连续的「鎮江」。PDF 第1至800页再按列扫过，没有认出镇江、丹徒或靖江。仍未核对，不并成一天。"
                "12月14日起并入南京那一块。" + PHRASE
            )
            s["dates_note"] = "镇江 1937-12-08 起，收到 1937-12-14。"
            s["sources"] = [
                "https://web.archive.org/web/20170809172042/http://www.jssdfz.gov.cn/book/jsz2/FL/FL.html",
                "http://lyj.jiangsu.gov.cn/art/2021/4/21/art_81813_9762633.html",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_长沙"):
            s["note"] = (
                "长沙县域。已核對《中華民國史事紀要》民國三十三年四月至六月，"
                "印页七二八（PDF 第735页），页眉民国三十三年六月十八日，写长沙沦陷，"
                "本日侵占全城，本（十八）日晨日军进攻长沙市街。"
                "1944-08-08 起并入下一块。" + PHRASE
            )
            s["dates_note"] = (
                "长沙 1944-06-18 起，收到 1944-08-08。已核對《中華民國史事紀要》印页七二八。"
            )
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13336.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_桂林"):
            s["note"] = (
                "桂林县域。已核對《中華民國史事紀要》民國三十三年十月至十二月，"
                "印页三七五（PDF 第383页），页眉民国三十三年十一月九日，写广西桂林本日为日军突入。"
                "1944-11-10 起并入桂柳走廊那一块。走廊其余县不提前到这一天。" + PHRASE
            )
            s["dates_note"] = (
                "桂林 1944-11-09 起，收到 1944-11-10。已核對《中華民國史事紀要》印页三七五。"
                "原图是 1944-11-10，改到这一天。"
            )
            s["name_zh"] = "日军军事占领区（桂林）"
            s["name_en"] = "日军军事占领区（桂林）"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13334.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_九江"):
            s["note"] = (
                "九江县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页一五九（PDF 第167页），页眉民国二十七年七月二十五、二十六日，写二十六日九江陷落。"
                "1939-03-27 起并入已经盖住这里的占领层。" + PHRASE
            )
            s["dates_note"] = "九江 1938-07-26 起，收到 1939-03-27。已核對《中華民國史事紀要》印页一五九。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_太原"):
            s["note"] = (
                "太原县域。已核對《中華民國史事紀要》民國二十六年七月至十二月，"
                "印页六四四（PDF 第652页），页眉民国二十六年十一月八日，"
                "写本日太原城北为日军侵入，傅作义率部向西山突围，太原遂陷日军手中。"
                + PHRASE
            )
            s["dates_note"] = "太原 1937-11-08 起，收到下一块盖住这里的日期。已核對《中華民國史事紀要》印页六四四。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13312.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_大同"):
            s["name_zh"] = "日军占领区（大同）"
            s["name_en"] = "日军占领区（大同）"
            s["controller"] = {"qid": "Q188712", "zh": "日军占领区"}
            s["note"] = (
                "大同县域。已核對《中華民國史事紀要》民國二十六年七月至十二月，"
                "印页四三一（PDF 第439页），页眉九月十四、十五日，追述十三日大同失陷。"
                "1937-10-28 起并入蒙古联盟自治政府，不把这一格提前记成那个政府。"
                + PHRASE
            )
            s["dates_note"] = (
                "大同 1937-09-13 起，收到 1937-10-28。追述，已核對《中華民國史事紀要》印页四三一。"
            )
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13312.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_保定"):
            s["name_zh"] = "日军占领区（保定）"
            s["name_en"] = "日军占领区（保定）"
            s["note"] = (
                "清苑县域。已核對《中華民國史事紀要》民國二十六年七月至十二月，"
                "印页四五二（PDF 第460页），页眉九月二十二日，写本日下午失陷，日军进占保定。"
                "印页四五四（PDF 第462页），页眉九月二十三、二十四日，写二十四日平汉线上之保定失守。"
                "史事纪要内记载不一。地图用较早且写本日的九月二十二日。"
                "1937-11-12 起并入下一块。" + PHRASE
            )
            s["dates_note"] = (
                "保定 1937-09-22 起，收到 1937-11-12。已核對印页四五二。"
                "印页四五四写二十四日失守，史事纪要内记载不一。"
            )
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13312.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_正定"):
            s["name_zh"] = "日军占领区（正定）"
            s["name_en"] = "日军占领区（正定）"
            s["note"] = (
                "正定县域。已核對《中華民國史事紀要》民國二十六年七月至十二月，"
                "印页五二五（PDF 第533页），页眉十月八、九日，写本日晨猛犯正定，十八时守军撤出，正定遂告失陷。"
                "印页五三四（PDF 第542页）追述八日正定失陷、九日石家庄告失。"
                "石家庄这一点落在正定县域，不另画一格。史事纪要内记载不一。地图用较早且写本日的十月八日。"
                "1937-11-12 起并入下一块。" + PHRASE
            )
            s["dates_note"] = (
                "正定 1937-10-08 起，收到 1937-11-12。已核對印页五二五。"
                "印页五三四追述九日石家庄告失，同一县域，史事纪要内记载不一。"
            )
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13312.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_永城"):
            s["name_zh"] = "中华民国维新政府（永城）"
            s["name_en"] = "中华民国维新政府（永城）"
            s["note"] = (
                "永城县域。已核對《中華民國史事紀要》民國二十七年一月至六月，"
                "印页四七八（PDF 第482页），页眉五月十七、十八日，追述本月十二日陷豫东之永城。"
                "1938-06-06 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "永城 1938-05-12 起，收到 1938-06-06。追述，已核對印页四七八。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13313.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_宿县"):
            s["name_zh"] = "中华民国维新政府（宿县）"
            s["name_en"] = "中华民国维新政府（宿县）"
            s["note"] = (
                "宿县县域。已核對《中華民國史事紀要》民國二十七年一月至六月，"
                "印页四七八（PDF 第482页），页眉五月十七、十八日，写十八日日军陷宿县、萧县。"
                "同页写十七日渡浍河，本日晚陷宿县。本日是十八日这一条。"
                "1938-06-06 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "宿县 1938-05-18 起，收到 1938-06-06。已核對印页四七八。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13313.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_萧县"):
            s["name_zh"] = "中华民国维新政府（萧县）"
            s["name_en"] = "中华民国维新政府（萧县）"
            s["note"] = (
                "萧县县域。已核對《中華民國史事紀要》民國二十七年一月至六月，"
                "印页四七八（PDF 第482页），页眉五月十七、十八日，写十八日日军陷宿县、萧县，并侵及徐州近郊。"
                "1938-06-06 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "萧县 1938-05-18 起，收到 1938-06-06。已核對印页四七八。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13313.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_晋城"):
            s["name_zh"] = "中华民国临时政府（晋城）"
            s["name_en"] = "中华民国临时政府（晋城）"
            s["controller"] = {"qid": "Q704714", "zh": "中华民国临时政府"}
            s["note"] = (
                "晋城县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页二六（PDF 第34页），页眉七月三、四日，四日这一条追述六月三十日攻陷天井关、晋城。"
                "印页一八二（PDF 第190页），页眉七月三十日，写本日克复沁水、阳城、晋城。"
                "从1937-11-12的华北色块里移出。收到七月三十日。" + PHRASE
            )
            s["until"] = "1938-07-30"
            s["dates_note"] = "晋城 1938-06-30 起，收到 1938-07-30。追述，已核對印页二六、一八二。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_阳城"):
            s["name_zh"] = "中华民国临时政府（阳城）"
            s["name_en"] = "中华民国临时政府（阳城）"
            s["controller"] = {"qid": "Q704714", "zh": "中华民国临时政府"}
            s["note"] = (
                "阳城县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页二六（PDF 第34页），页眉七月三、四日，四日这一条写本日复陷阳城。"
                "印页一八二（PDF 第190页），页眉七月三十日，写本日克复沁水、阳城、晋城。"
                "从1937-11-12的华北色块里移出。收到七月三十日。" + PHRASE
            )
            s["until"] = "1938-07-30"
            s["dates_note"] = "阳城 1938-07-04 起，收到 1938-07-30。已核對印页二六、一八二。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_湖口"):
            s["name_zh"] = "中华民国维新政府（湖口）"
            s["name_en"] = "中华民国维新政府（湖口）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "湖口县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页三三（PDF 第41页），页眉七月五日，写四日下午突破防线，本日晨湖口陷落。"
                "1939-03-27 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "湖口 1938-07-05 起，收到 1939-03-27。已核對印页三三。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_沁水"):
            s["name_zh"] = "中华民国临时政府（沁水）"
            s["name_en"] = "中华民国临时政府（沁水）"
            s["controller"] = {"qid": "Q704714", "zh": "中华民国临时政府"}
            s["note"] = (
                "沁水县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页六五（PDF 第73页），页眉七月七日，写本日第十四师由阳城攻占沁水。"
                "印页一八二（PDF 第190页），页眉七月三十日，写本日克复沁水、阳城、晋城。"
                "从1937-11-12的华北色块里移出。收到七月三十日。" + PHRASE
            )
            s["until"] = "1938-07-30"
            s["dates_note"] = "沁水 1938-07-07 起，收到 1938-07-30。已核對印页六五、一八二。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_翼城"):
            s["name_zh"] = "中华民国临时政府（翼城）"
            s["name_en"] = "中华民国临时政府（翼城）"
            s["controller"] = {"qid": "Q704714", "zh": "中华民国临时政府"}
            s["note"] = (
                "翼城县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页九九（PDF 第107页），页眉七月十一日，写本日陷翼城，我军退守中条山区。"
                "印页二一五（PDF 第223页），页眉八月三日，写本日第八十三师攻克翼城。"
                "从1937-11-12的华北色块里移出。收到八月三日。" + PHRASE
            )
            s["until"] = "1938-08-03"
            s["dates_note"] = "翼城 1938-07-11 起，收到 1938-08-03。已核對印页九九、二一五。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_太湖"):
            s["name_zh"] = "中华民国维新政府（太湖）"
            s["name_en"] = "中华民国维新政府（太湖）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "太湖县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页一六一（PDF 第169页），页眉七月二十六日，"
                "写二十四日今村支队突破黄泥港，二十五日向太湖猛攻，本日中午太湖失陷。"
                "印页三一一（PDF 第319页），页眉八月二十七日，写本日将太湖克复。"
                "收到八月二十七日。1938-10-21 起仍并入下一块。" + PHRASE
            )
            s["until"] = "1938-08-27"
            s["dates_note"] = "太湖 1938-07-26 起，收到 1938-08-27。已核對印页一六一、三一一。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_宿松"):
            s["name_zh"] = "中华民国维新政府（宿松）"
            s["name_en"] = "中华民国维新政府（宿松）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["until"] = "1938-08-28"
            s["note"] = (
                "宿松县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页二〇四（PDF 第212页），页眉八月一日，写本日守军退守独山，宿松遂陷。"
                "印页三三三（PDF 第341页），页眉八月二十八日，写克复宿松。"
                "收到八月二十八日。1938-10-21 起仍并入下一块。" + PHRASE
            )
            s["dates_note"] = "宿松 1938-08-01 起，收到 1938-08-28。已核對印页二〇四、三三三。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_黄梅"):
            s["name_zh"] = "中华民国维新政府（黄梅）"
            s["name_en"] = "中华民国维新政府（黄梅）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "黄梅县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页二一五（PDF 第223页）至印页二一六（PDF 第224页），页眉八月三日，"
                "追述迄本月二日止，当晚黄梅县城遂陷。"
                "1938-10-21 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "黄梅 1938-08-02 起，收到 1938-10-21。追述，已核對印页二一五、二一六。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_瑞昌"):
            s["name_zh"] = "中华民国维新政府（瑞昌）"
            s["name_en"] = "中华民国维新政府（瑞昌）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "瑞昌县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页二九四（PDF 第302页），页眉八月二十四日，写东门倾塌，日军冲入城内。"
                "印页三〇二（PDF 第310页）再写二十四日攻占瑞昌。"
                "1939-03-27 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "瑞昌 1938-08-24 起，收到 1939-03-27。已核對印页二九四、三〇二。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_六安"):
            s["name_zh"] = "中华民国维新政府（六安）"
            s["name_en"] = "中华民国维新政府（六安）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "六安县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页三三四（PDF 第342页），页眉八月二十八、二十九日，写本日分三路进攻六安，六安遂陷。"
                "印页三三八（PDF 第346页）写二十八日陷六安。收到下一块。" + PHRASE
            )
            s["dates_note"] = "六安 1938-08-28 起，收到 1938-10-21。已核對印页三三四、三三八。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_霍山"):
            s["name_zh"] = "中华民国维新政府（霍山）"
            s["name_en"] = "中华民国维新政府（霍山）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "霍山县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页三三八（PDF 第346页），页眉八月二十九日，写本日攻霍山，霍山遂告失守。"
                "1938-10-21 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "霍山 1938-08-29 起，收到 1938-10-21。已核對印页三三八。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_广济"):
            s["name_zh"] = "中华民国维新政府（广济）"
            s["name_en"] = "中华民国维新政府（广济）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "广济县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页三六二（PDF 第370页），页眉九月六日，写本日突破卓木尖，广济遂告陷落。"
                "1938-10-21 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "广济 1938-09-06 起，收到 1938-10-21。已核對印页三六二。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_黄陂"):
            s["name_zh"] = "日军占领区（黄陂）"
            s["name_en"] = "日军占领区（黄陂）"
            s["note"] = (
                "黄陂县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页五八〇（PDF 第588页），页眉十月二十五日，追述本月二十四日侵陷黄陂。"
                "1938-10-25 起并入武汉周边那一块。" + PHRASE
            )
            s["dates_note"] = "黄陂 1938-10-24 起，收到 1938-10-25。追述，已核對印页五八〇。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_通山"):
            s["name_zh"] = "日军占领区（通山）"
            s["name_en"] = "日军占领区（通山）"
            s["note"] = (
                "通山县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页六三四（PDF 第642页），页眉十一月四日，写本日通山陷落。"
                "从1938-10-25的武汉周边色块里移出。1939-03-27 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "通山 1938-11-04 起，收到 1939-03-27。已核對印页六三四。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_崇阳"):
            s["name_zh"] = "日军占领区（崇阳）"
            s["name_en"] = "日军占领区（崇阳）"
            s["until"] = "1938-11-17"
            s["note"] = (
                "崇阳县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页六七四（PDF 第682页），页眉十一月十七、十八日，写本月六日侵占崇阳，这一条写克复崇阳。"
                "十八日是长沙大火案另一条。从1938-10-25的武汉周边色块里移出。收到十一月十七日。"
                + PHRASE
            )
            s["dates_note"] = "崇阳 1938-11-06 起，收到 1938-11-17。已核對印页六七四。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_固始"):
            s["name_zh"] = "中华民国维新政府（固始）"
            s["name_en"] = "中华民国维新政府（固始）"
            s["controller"] = {"qid": "Q708865", "zh": "中华民国维新政府"}
            s["note"] = (
                "固始县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页六二一（PDF 第629页），页眉十月三十一日，追述九月二日之后，六日陷固始。"
                "1938-10-21 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "固始 1938-09-06 起，收到 1938-10-21。追述，已核對印页六二一。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_罗山"):
            s["name_zh"] = "日军占领区（罗山）"
            s["name_en"] = "日军占领区（罗山）"
            s["note"] = (
                "罗山县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页六二一（PDF 第629页），页眉十月三十一日，同一段追述九月二十一日罗山被陷。"
                "1938-10-25 起并入武汉周边那一块。" + PHRASE
            )
            s["dates_note"] = "罗山 1938-09-21 起，收到 1938-10-25。追述，已核對印页六二一。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_鄂城"):
            s["name_zh"] = "日军占领区（鄂城）"
            s["name_en"] = "日军占领区（鄂城）"
            s["note"] = (
                "鄂城县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页五六二（PDF 第570页），页眉十月二十二日，写本日中午鄂城陷落。"
                "1938-10-25 起并入武汉周边那一块。" + PHRASE
            )
            s["dates_note"] = "鄂城 1938-10-22 起，收到 1938-10-25。已核對印页五六二。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_通城"):
            s["name_zh"] = "日军占领区（通城）"
            s["name_en"] = "日军占领区（通城）"
            s["note"] = (
                "通城县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页六四六（PDF 第654页），页眉十一月八、九、十日，写九日日军侵占湖北通城。"
                "1931 年治所用湖北这一格，不是安徽同名点。1939-03-27 起并入下一块。" + PHRASE
            )
            s["dates_note"] = "通城 1938-11-09 起，收到 1939-03-27。已核對印页六四六。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if s["id"].endswith("_天津"):
            s["name_zh"] = "日军占领区（天津）"
            s["name_en"] = "日军占领区（天津）"
            s["note"] = (
                "天津县域。已核對《中華民國史事紀要》民國二十六年七月至十二月，"
                "印页二一六（PDF 第224页），页眉七月三十日，"
                "写天津市本日陷于日军手中。同页写北平已被包围、四郊为日军所控制，不把北平写成已经入城。"
                "1937-08-15 起并入华北日占区。" + PHRASE
            )
            s["dates_note"] = "天津 1937-07-30 起，收到 1937-08-15。已核對《中華民國史事紀要》印页二一六。"
            s["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13312.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        for key, info in CHRONICLE_1944.items():
            if not s["id"].endswith("_" + key):
                continue
            s["name_zh"] = info["name_zh"]
            s["name_en"] = info["name_zh"]
            s["note"] = info["note"] + PHRASE
            s["dates_note"] = info["dates"]
            s["sources"] = info["sources"]
    doc["zones"].extend(supplements)

    for name, points, fall, end, controller, name_zh, why in GROWTH:
        ids = []
        for lon, lat in points:
            cid = cell_at(features, tree, lon, lat)
            if cid and cid not in ids:
                ids.append(cid)
        if len(ids) != len(points):
            print("NO CELL", name, ids)
            continue
        for z in converted:
            if (z.get("from") or "") < fall and any(i in z["geometry"]["roc_counties"] for i in ids):
                z["geometry"]["roc_counties"] = [i for i in z["geometry"]["roc_counties"] if i not in ids]
                print("strip", name, z["id"])
        sid = f"sjw_cell_{'_'.join(i.split(':')[-1] for i in ids)}_{fall}_{name}"
        if any(z["id"] == sid for z in doc["zones"]):
            continue
        supplements_extra = {
            "id": sid,
            "group": "sino_japanese_war",
            "kind": "occupied",
            "as_polity": True,
            "name_zh": name_zh,
            "name_en": name_zh,
            "controller": controller,
            "from": fall,
            "until": end,
            "geometry": {"roc_counties": ids},
            "approx": True,
            "note": f"{why} {PHRASE}未核对《中華民國史事紀要》。",
            "dates_note": f"{name} {fall} 起，收到 {end}。",
            "sources": {
                "安庆": ["https://zh.wikipedia.org/wiki/武汉会战", "https://zenodo.org/records/5721459"],
                "宜昌": ["https://zh.wikipedia.org/wiki/枣宜会战", "https://zenodo.org/records/5721459"],
                "海口": ["https://zh.wikipedia.org/wiki/日本侵佔海南島", "https://zenodo.org/records/5721459"],
                "汕头": [
                    "https://www.shantou.gov.cn/stszrzyj/zwgk/gzdt/content/post_2449128.html",
                    "https://daj.shantou.gov.cn/daj/kzda/201506/7f8b9a33ebf04ed8bb12c0cbecc8b78d.shtml",
                    "https://zenodo.org/records/5721459",
                ],
                "南宁": ["https://zh.wikipedia.org/wiki/桂南会战", "https://zenodo.org/records/5721459"],
                "惠阳": ["https://www.drnh.gov.tw/p/404-1003-13314.php?Lang=zh-tw", "https://zenodo.org/records/5721459"],
                "连江": ["https://www.drnh.gov.tw/p/404-1003-13323.php?Lang=zh-tw", "https://zenodo.org/records/5721459"],
                "长乐": ["https://www.drnh.gov.tw/p/404-1003-13323.php?Lang=zh-tw", "https://zenodo.org/records/5721459"],
                "福州": ["http://fz.fjdsfzw.org.cn/2015-11-19/content_85283.html", "https://zenodo.org/records/5721459"],
                "衡阳": ["https://zh.wikipedia.org/wiki/衡阳保卫战", "https://zenodo.org/records/5721459"],
                "柳州": ["https://zh.wikipedia.org/wiki/桂柳会战", "https://zenodo.org/records/5721459"],
            }[name],
        }
        if name in ("连江", "长乐"):
            supplements_extra["note"] = (
                f"{name}县域。已核對《中華民國史事紀要》民國三十年一月至六月，"
                "印页四二五（PDF 第432页），页眉四月二十四日，追述十九日下午陷连江、长乐。"
                "没有写这两县收到哪一天。结束日用福州这一格的 1941-09-03，结束日待考。"
                + PHRASE
            )
            supplements_extra["dates_note"] = (
                f"{name} 1941-04-19 起，收到 1941-09-03。追述，已核對印页四二五。结束日待考。"
            )
        if name == "惠阳":
            supplements_extra["note"] = (
                "惠阳县域。已核對《中華民國史事紀要》民國二十七年七月至十二月，"
                "印页五五五（PDF 第563页），页眉十月二十一日，追述本月十五日惠阳失守。"
                "印页六九二（PDF 第700页）写十二日克复惠阳。不在既有大块里，收到十一月十二日。"
                + PHRASE
            )
            supplements_extra["dates_note"] = (
                "惠阳 1938-10-15 起，收到 1938-11-12。追述，已核對印页五五五、六九二。"
            )
        if name == "安庆" and fall == "1938-06-13":
            supplements_extra["note"] = (
                "怀宁县域。已核對《中華民國史事紀要》民國二十七年一月至六月，"
                "印页五六三（PDF 第567页），页眉六月十三日，写十一日日军在怀宁（安庆）试图登陆被击退，"
                "十二日日舰轰击并掩护登陆，机场首先失守。"
                "印页五六四（PDF 第568页），页眉六月十三、十四日，写至本日晨城垣亦陷。"
                "不把十二日的登陆和机场失守写成城垣已经陷落。从1938-06-13起。"
                "6月6日的色块更早，从那一块移出。桐城不另画。1940-03-30起改记汪精卫政权。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "安庆 1938-06-13 起，收到 1940-03-30。已核對《中華民國史事紀要》印页五六三、五六四。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13313.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "宜昌":
            supplements_extra["note"] = (
                "宜昌县域。1940-06-12 起，收到 1945-08-16。"
                "已核對《中華民國史事紀要》民國二十九年一月至六月，"
                "印页七一一（PDF 第717页），页眉六月十七日，写十二日拂晓日军衝入宜昌城內，巷战至十一时。"
                "印页七一二（PDF 第718页）写第十八师主力十二日晚转进，并写十六晚收回宜昌。"
                "这是战报汇编，注出重庆《中央日报》六月十八日。不把这一次收回写成占领已经结束，结束日不改。"
                "印页六九一（PDF 第698页）是重庆空战，没有宜昌。原来的手绘范围没有盖住这个治所，不把邻近县加进来。"
                + PHRASE
            )
            supplements_extra["dates_note"] = (
                "宜昌 1940-06-12 起，收到 1945-08-16。已核對《中華民國史事紀要》印页七一一、七一二。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13318.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "福州" and fall == "1941-04-22":
            supplements_extra["note"] = (
                "福州和闽侯两个治所几乎叠在一起，两格都画。"
                "已核對《中華民國史事紀要》民國三十年一月至六月，"
                "印页四二五（PDF 第432页），页眉四月二十四日，写二十一日另一股在长门登陆，与北股会合犯福州，"
                "福州地滨东海，固守不易，我军已于二十二日午后退出。"
                "不把二十一日的进犯写成已经退出。连江、长乐同页写十九日陷落，两县另画到九月三日，结束日待考。"
                "9 月 3 日撤出。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "福州 1941-04-22 起，收到 1941-09-03。已核對《中華民國史事紀要》印页四二五。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13323.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "柳州":
            supplements_extra["note"] = (
                "1931 年治所仍名马平。已核對《中華民國史事紀要》民國三十三年十月至十二月，"
                "印页四二三（PDF 第431页），页眉民国三十三年十一月十一日，写广西柳州本日为日军攻占，"
                "并写柳州继桂林失陷。桂柳走廊的手绘范围没有盖住这个治所，"
                "控制方沿用那一条的日军军事占领，不是汪政权。"
                "收复已核對《中華民國史事紀要》民國三十四年五月至七月，"
                "印页五二八（PDF 第530页），页眉六月二十九日，写本日克复柳州全城。"
                "沦陷日仍是十一月十一日。收到六月二十九日，不含当天。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "柳州 1944-11-11 起，收到 1945-06-29。"
                "沦陷已核對印页四二三，收复已核對印页五二八。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13334.php?Lang=zh-tw",
                "https://www.drnh.gov.tw/p/404-1003-13342.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "汕头":
            supplements_extra["note"] = (
                "汕头市区落在 1931 年朝阳治所的单元格里，澄海治所也在原来的汕头方框里。"
                "已核對《中華民國史事紀要》民國二十八年一月至六月，印页七二一（PDF 第731页），"
                "页眉民国二十八年六月二十一日，写日军陷广东汕头，本日在汕头附近登陆，守军退出汕头。"
                "两格从 1939-06-21 起，不再从 3 月 27 日起。潮安不在这框里。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "汕头 1939-06-21 起，收到 1940-03-30。已核對《中華民國史事紀要》印页七二一。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13315.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "南宁" and fall == "1939-11-24":
            supplements_extra["note"] = (
                "邕宁县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
                "印页六一二（PDF 第617页），页眉民国二十八年十一月二十四日，"
                "标题日军侵陷广西南宁，写本日拂晓日军强渡邕江，苦战至午后南宁遂告不守。"
                "收复已核對《中華民國史事紀要》民國二十九年七月至十二月，"
                "印页四八五至四八六（PDF 第492–493页），页眉民国二十九年十月二十九日，"
                "标题我军收复广西省南宁，写二十八日晚日军放弃南宁。"
                "这一格收到 1940-10-29，不含当天。1944 年 11 月的第二次占领不在这一格里。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "南宁 1939-11-24 起，收到 1940-10-29。沦陷已核對印页六一二，收复已核對印页四八五。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13317.php?Lang=zh-tw",
                "https://www.drnh.gov.tw/p/404-1003-13320.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "衡阳":
            supplements_extra["note"] = (
                "衡阳县域。已核對《中華民國史事紀要》民國三十三年七月至九月，"
                "印页三九六（PDF 第404页），页眉民国三十三年八月八日，"
                "标题衡阳经四十七日血战沦陷，写日军本日突入中央银行、第十军军部。"
                "原来的湖南手绘范围没有盖住这个治所。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "衡阳 1944-08-08 起，收到 1945-08-16。已核對《中華民國史事紀要》印页三九六。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13338.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        if name == "海口" and fall == "1939-02-10":
            supplements_extra["note"] = (
                "海口治所的单元格。已核對《中華民國史事紀要》民國二十八年一月至六月，"
                "印页二二〇（PDF 第220页），页眉民国二十八年二月十日，写海口于下午三时陷敌。"
                "琼山和岛上其余县仍从 1939-03-27 的海南块起，不提前。" + PHRASE
            )
            supplements_extra["dates_note"] = (
                "海口 1939-02-10 起，收到 1940-03-30。已核對《中華民國史事紀要》印页二二〇。"
            )
            supplements_extra["sources"] = [
                "https://www.drnh.gov.tw/p/404-1003-13315.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ]
        doc["zones"].append(supplements_extra)
        print("growth", name, fall, end, ids)

    harbin = "mcgd:s417"
    if harbin in id_of and not any(z["id"] == "ccw_harbin_1946" for z in doc["zones"]):
        doc["zones"].append({
            "id": "ccw_harbin_1946",
            "group": "ccw_manchuria",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "共军控制区（哈尔滨）",
            "name_en": "CCP-held Harbin",
            "controller": {"qid": "Q17427", "zh": "中国共产党"},
            "from": "1946-04-28",
            "until": "1946-06-07",
            "geometry": {"roc_counties": [harbin]},
            "approx": True,
            "note": "滨江县域。1946-04-28 进入哈尔滨。哈尔滨在吉林的滨江，不在黑龙江多边形里，也不把吉林全省提前。1946-06-07 起并入松花江以北的东北沦陷区。民国三十五年四月至六月，PDF 第342页有二十九日的标题，同页写四月二十八、二十九日的粮食，没有哈尔滨。PDF 第300至380页和 PDF 第360至640页按列扫过，没有认出哈尔滨、齐齐哈尔或嫩江。PDF 第100至520页再按列扫过，没有认出滨江、北满或齐齐哈尔。大致。县域为治所泰森多边形近似。未核对《中華民國史事紀要》。",
            "dates_note": "1946-04-28 起，收到 1946-06-07。",
            "sources": ["http://www.chinadaily.com.cn/dfpd/hlj/2011-04/28/content_12413529.htm", "https://zenodo.org/records/5721459"],
        })
        print("added harbin cell")

    jinzhou = ["mcgd:s143", "mcgd:D3064040"]
    if all(i in id_of for i in jinzhou) and not any(z["id"] == "ccw_jinzhou_1948" for z in doc["zones"]):
        doc["zones"].append({
            "id": "ccw_jinzhou_1948",
            "group": "ccw_manchuria",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "共军控制区（锦州）",
            "name_en": "CCP-held Jinzhou",
            "controller": {"qid": "Q17427", "zh": "中国共产党"},
            "from": "1948-10-15",
            "until": "1948-11-01",
            "geometry": {"roc_counties": jinzhou},
            "approx": True,
            "note": (
                "1931年锦县治所和锦州点两个单元格，不是锦州周围各县。"
                "已核對《中華民國史事紀要》民國三十七年七月至十二月，"
                "印页六五一至六五二（PDF 第658–659页），页眉民国三十七年十月十五日，"
                "写十四日夜共军突入锦州市区，截至十五日拂晓市内大部为共军侵入，"
                "范汉杰、卢浚泉被俘，中午战事仍在继续。"
                "图上从 1948-10-15 起记沦陷，不改到十四日夜。"
                "这一天以前从东北沦陷区里挖出，不把三月就涂成共军。"
                "1948-11-01 起并入辽宁。大致。县域为治所泰森多边形近似。"
            ),
            "dates_note": "锦州 1948-10-15 起，收到 1948-11-01。已核對《中華民國史事紀要》印页六五一。",
            "sources": [
                "https://www.drnh.gov.tw/p/404-1003-13357.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ],
        })
        print("added jinzhou cell")

    yangzhou = "mcgd:s1175"
    if yangzhou in id_of and not any(z["id"] == "ccw_yangzhou_1949" for z in doc["zones"]):
        doc["zones"].append({
            "id": "ccw_yangzhou_1949",
            "group": "chinese_civil_war",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "共军控制区（扬州）",
            "name_en": "CCP-held Yangzhou",
            "controller": {"qid": "Q17427", "zh": "中国共产党"},
            "from": "1949-01-23",
            "until": "1949-04-23",
            "geometry": {"roc_counties": [yangzhou]},
            "approx": True,
            "note": (
                "江都县域，不是扬州周围各县。"
                "已核對《中華民國史事紀要》民國三十八年一月至六月，"
                "PDF 第240页，页眉一月二十二、二十三日，"
                "写二十三日滁县、扬州为共军攻占，国军改在浦镇、瓜洲布防。"
                "六合、滁县不另画。1949-04-23 起并入江苏整省。"
                "大致。县域为治所泰森多边形近似。"
            ),
            "dates_note": "扬州 1949-01-23 起，收到 1949-04-23。已核對《中華民國史事紀要》PDF 第240页。",
            "sources": [
                "https://www.drnh.gov.tw/p/404-1003-13361.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ],
        })
        print("added yangzhou cell")

    tianshui = "mcgd:s742"
    if tianshui in id_of and not any(z["id"] == "ccw_tianshui_1949" for z in doc["zones"]):
        doc["zones"].append({
            "id": "ccw_tianshui_1949",
            "group": "chinese_civil_war",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "共军控制区（天水）",
            "name_en": "CCP-held Tianshui",
            "controller": {"qid": "Q17427", "zh": "中国共产党"},
            "from": "1949-08-02",
            "until": "1949-08-26",
            "geometry": {"roc_counties": [tianshui]},
            "approx": True,
            "note": (
                "天水县域，不是西兰公路沿线。"
                "已核對《中華民國史事紀要》民國三十八年七月至九月，"
                "印页一六九（PDF 第177页），页眉八月二日，"
                "写甘肃天水及江西遂川失守，本日天水失守。"
                "遂川不另画。1949-08-26 起并入甘肃整省。"
                "大致。县域为治所泰森多边形近似。"
            ),
            "dates_note": "天水 1949-08-02 起，收到 1949-08-26。已核對《中華民國史事紀要》印页一六九。",
            "sources": [
                "https://www.drnh.gov.tw/p/404-1003-13363.php?Lang=zh-tw",
                "https://zenodo.org/records/5721459",
            ],
        })
        print("added tianshui cell")

    # 1944 年南宁是第二次占领。不走 GROWTH：那一条会把 1939 年已经结束的格子拆掉。
    nanning_id = "sjw_cell_s670_1944-11-24_南宁"
    if not any(z.get("id") == nanning_id for z in doc["zones"]):
        cid = cell_at(features, tree, 108.29251, 22.80864)
        if not cid:
            print("NANNING2 NO CELL")
        else:
            doc["zones"].append({
                "id": nanning_id,
                "group": "sino_japanese_war",
                "kind": "occupied",
                "as_polity": True,
                "name_zh": "日军军事占领区（南宁）",
                "name_en": "日军军事占领区（南宁）",
                "controller": JP,
                "from": "1944-11-24",
                "until": "1945-05-27",
                "geometry": {"roc_counties": [cid]},
                "approx": True,
                "note": (
                    "邕宁县域。一九三九年那一格仍收到 1940-10-29。"
                    "已核對《中華民國史事紀要》民國三十三年十月至十二月，"
                    "印页七一六（PDF 第724页），写第六方面军第二十三军先于十一月二十四日攻入广西南宁。"
                    "收复已核對《中華民國史事紀要》民國三十四年五月至七月，"
                    "印页二九七（PDF 第299页），页眉六月三日，注写第六十四军一五六师于五月廿七日克南宁。"
                    "这一格收到五月二十七日，不含当天。不在桂柳走廊那一块里。"
                    + PHRASE
                ),
                "dates_note": (
                    "南宁 1944-11-24 起，收到 1945-05-27。"
                    "攻入已核對印页七一六，克复已核對印页二九七。追述。"
                ),
                "sources": [V33_1012, V34_57, ZENODO],
            })
            print("added nanning 1944", cid)

    if not any(z["id"] == "sjw_ccp_central_soviet" for z in doc["zones"]):
        doc["zones"].append({
            "id": "sjw_ccp_central_soviet",
            "group": "ccp_base",
            "kind": "de_facto",
            "as_polity": True,
            "name_zh": "中央苏区（中共根据地，大致范围）",
            "name_en": "Central Soviet Area",
            "controller": {"qid": "Q1135255", "zh": "中华苏维埃共和国"},
            "from": "1931-11-07",
            "until": "1934-10-17",
            "geometry": {"roc_counties": by_name(features, SOVIET)},
            "approx": True,
            "note": "大致。县域为治所泰森多边形近似。1934年9月记载里剩下的瑞金、会昌、雩都、兴国、宁都、石城、宁化、长汀八个县城，不是辖境，也不是县界。未核对《中華民國史事紀要》。",
            "dates_note": "1931-11-07 成立。1934-10-17 中央红军由雩都出发，这一天起不再画这八个县域。",
            "sources": [
                "https://zh.wikipedia.org/wiki/中华苏维埃共和国",
                "https://zh.wikipedia.org/wiki/长征",
                "https://zenodo.org/records/5721459",
            ],
        })
        print("added central soviet", len(SOVIET))

    # 纪要写明收复日、而且该县已经在大块里：收到收复日，并从这一天之后的大块里移出。
    # 跨过收复日的那一块改成单独的县域，控制方沿用那一块。
    qlabel = {
        "Q704714": "中华民国临时政府",
        "Q708865": "中华民国维新政府",
        "Q188712": "日军占领区",
        "Q696242": "汪精卫政权",
        "Q905486": "华北政务委员会",
    }
    vol28 = "https://www.drnh.gov.tw/p/404-1003-13317.php?Lang=zh-tw"
    recovered = [
        ("武乡", 112.97659, 36.74750, "1939-07-11",
         "武乡县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页三七（PDF 第45页），页眉七月十二、十三日。十二日这一条追述十一日克复武乡。"
         "县在华北大块里，收到一九三九年七月十一日，之后从大块里移出。"),
        ("襄垣", 113.15479, 36.41955, "1939-07-12",
         "襄垣县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页三七（PDF 第45页），页眉七月十二、十三日。十二日这一条写本日晨襄垣克复。"
         "十三日是财政部另一条。县在华北大块里，收到一九三九年七月十二日。"),
        ("阳城", 112.49422, 35.50255, "1939-07-25",
         "阳城县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页八三（PDF 第91页），页眉七月二十六日，追述二十五日晨克复阳城。"
         "一九三八年七月那一格仍收到七月三十日。这一次是县在华北大块里，收到一九三九年七月二十五日。"),
        ("沁水", 112.23888, 35.74570, "1939-07-26",
         "沁水县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页八三（PDF 第91页），页眉七月二十六日，写迄二十六日晚克复沁水。"
         "一九三八年七月那一格仍收到七月三十日。这一次收到一九三九年七月二十六日。"),
        ("崇阳", 114.0420, 29.5768, "1939-07-25",
         "崇阳县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页八四（PDF 第92页），页眉七月二十六日，追述二十五日晚攻克崇阳城。"
         "一九三八年十一月那一格仍收到十一月十七日。这一次县在华中大块里，收到一九三九年七月二十五日。"),
        ("林县", 113.85154, 36.02068, "1939-08-02",
         "林县县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页一一五（PDF 第122页），页眉八月四、五日，追述二日克复林县。"
         "县在华北大块里，收到一九三九年八月二日。"),
        ("来安", 118.46423, 32.44413, "1939-09-05",
         "来安县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页二二八（PDF 第234页），页眉九月五日，写本日克复来安县城。"
         "县在维新政府大块里，收到一九三九年九月五日。"),
        ("通山", 114.4833, 29.6345, "1939-09-14",
         "通山县域。已核對《中華民國史事紀要》民國二十八年七月至十二月，"
         "印页二八八（PDF 第294页），页眉九月十四、十五日。通山这一条在十五日教育部令之前，"
         "写本日下午三时第三度收复通山县城。十五日是另一条。收到一九三九年九月十四日。"),
        ("桂林", 110.16441, 25.34684, "1945-07-27",
         "桂林县域。沦陷日仍是 1944-11-09，印页三七五不改。"
         "收复已核對《中華民國史事紀要》民國三十四年五月至七月，"
         "印页九二九（PDF 第931页），页眉七月二十六、二十七日，标题在二十七日下，写本日攻克桂林。"
         "印页九三一（PDF 第933页），页眉七月二十七日，写二十七日午后十时完全克复桂林。"
         "从桂柳走廊移出，收到七月二十七日，不含当天。"),
    ]
    for name, lon, lat, end, why in recovered:
        cid = cell_at(features, tree, lon, lat)
        if not cid:
            print("RECOVERY NO CELL", name)
            continue
        spanning = None
        for z in doc["zones"]:
            geom = z.get("geometry") or {}
            ids = geom.get("roc_counties")
            if not ids or cid not in ids:
                continue
            # 只动日军占领层。晋冀鲁豫等根据地 kind 是 de_facto，收复日不从那里移出。
            if z.get("kind") != "occupied":
                continue
            frm = z.get("from") or ""
            until = z.get("until") or "9999-12-31"
            if until <= end:
                continue
            if frm >= end:
                geom["roc_counties"] = [i for i in ids if i != cid]
                print("recovery strip", name, z["id"])
                continue
            geom["roc_counties"] = [i for i in ids if i != cid]
            if spanning is None or frm > (spanning.get("from") or ""):
                spanning = z
            print("recovery split", name, z["id"], frm, until)
        if spanning is None:
            print("RECOVERY NO SPAN", name)
            continue
        qid = (spanning.get("controller") or {}).get("qid") or ""
        label = f"{qlabel.get(qid, spanning.get('name_zh') or '日军占领区')}（{name}）"
        sid = f"sjw_cell_{cid}_{end}_{name}"
        if any(z.get("id") == sid for z in doc["zones"]):
            continue
        doc["zones"].append({
            "id": sid,
            "group": "sino_japanese_war",
            "kind": "occupied",
            "as_polity": True,
            "name_zh": label,
            "name_en": label,
            "controller": spanning["controller"],
            "from": spanning.get("from"),
            "until": end,
            "geometry": {"roc_counties": [cid]},
            "approx": True,
            "note": why + PHRASE,
            "dates_note": (
                f"桂林收到 {end}。沦陷日仍是 1944-11-09。已核對印页九二九、九三一。"
                if name == "桂林"
                else f"{name}收到 {end}。已核對《中華民國史事紀要》民國二十八年七月至十二月。追述或本日见原文。"
            ),
            "sources": (
                ["https://www.drnh.gov.tw/p/404-1003-13342.php?Lang=zh-tw", "https://zenodo.org/records/5721459"]
                if name == "桂林"
                else [vol28, "https://zenodo.org/records/5721459"]
            ),
        })
        print("recovery cell", name, spanning.get("from"), end, cid, label)

    EXTENTS.write_text(json.dumps(extents, ensure_ascii=False, indent=1), encoding="utf-8")
    ZONES.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("zones", len(doc["zones"]), "extents", len(extents))

    bei = json.loads(BEIYANG.read_text(encoding="utf-8"))
    before = len(bei["fronts"])
    bei["fronts"] = [f for f in bei["fronts"] if f.get("id") != "soviet-ring"]
    for war in bei["wars"]:
        if war.get("id") == "soviet-1931":
            war["note"] = (
                "中文维基百科《中华苏维埃共和国》记1931-11-07成立。《长征》记1934年9月下旬中央苏区只剩"
                "瑞金、会昌、雩都、兴国、宁都、石城、宁化、长汀一带，10月17日中央红军由雩都出发。"
                "这八个县城各用治所泰森多边形近似，大致范围，不是辖境，也不是县界。直边环线已撤。未核对《中華民國史事紀要》。"
            )
    BEIYANG.write_text(json.dumps(bei, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("fronts", before, "->", len(bei["fronts"]))


if __name__ == "__main__":
    main()
