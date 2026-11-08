#!/usr/bin/env python3
"""
生成 data/curated/control_zones.json 中的中日战争（1931–1945）、太平洋战争东南亚日占区、1945–48 东北的实际控制区条目
（group = sino_japanese_war / ww2_asia / ccw_manchuria；重复运行会先删掉这些 group 再写入）。

依据：USMA 历史系 Chinese Civil War 地图集「Japanese Occupation, 1940」「Situation at the End of World War II」、
维基百科各战役/政权条目（城市易手日期）。日占区是「点和线」式控制：城市与铁路沿线由日军控制，广大乡村有国民革命军游击区与
共军根据地，地图上的连续色块只是大致范围（精度约 ±50–150 km），每条注明来源与精度。
术语：中华民国国军写作「国民革命军」，中共武装写作「共军」。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "data" / "curated" / "control_zones.json"
WP = "https://en.wikipedia.org/wiki/"
ZWP = "https://zh.wikipedia.org/wiki/"
USMA = "https://dhc.westpoint.edu/atlases/（USMA 历史系 Chinese Civil War 地图集：{}）"
GROUPS = {"sino_japanese_war", "ww2_asia", "ccw_manchuria"}

# ---- 日占区（中国关内）阶梯节点 ----
NORTH_1937 = [[115.4, 40.1], [115.8, 40.4], [116.2, 40.9], [117.3, 40.6], [118.5, 40.2], [119.7, 40.1], [119.3, 39.3], [118.0, 39.0], [117.6, 38.5],
              [117.5, 38.0], [116.5, 37.3], [115.0, 37.6], [114.2, 38.2], [114.0, 38.8], [114.5, 39.5], [115.0, 39.9]]
NORTH_1938 = [[115.4, 40.1], [115.8, 40.4], [116.2, 40.9], [117.3, 40.6], [118.5, 40.2], [119.7, 40.1], [119.3, 39.3], [118.0, 39.0], [117.6, 38.5],
              [118.5, 38.0], [119.0, 37.3], [120.5, 37.8], [122.6, 37.4], [120.3, 36.0], [119.2, 35.0], [118.0, 35.0], [117.7, 34.7], [116.5, 35.4],
              [115.5, 36.0], [114.35, 36.0], [113.9, 35.3], [113.4, 35.4], [112.5, 35.0], [110.5, 35.0], [110.5, 36.5], [111.0, 37.5], [111.4, 38.6],
              [112.2, 38.9], [113.4, 39.3], [114.4, 39.6]]
LOWER_YANGTZE_1937 = [[121.9, 31.7], [120.9, 32.1], [119.4, 32.4], [118.6, 32.1], [118.2, 31.4], [118.4, 31.0], [118.6, 30.9], [119.6, 30.5],
                      [120.2, 30.2], [121.0, 30.6], [121.9, 30.85]]
# 1938-06：徐州会战后津浦线贯通，合肥、安庆、开封失守 → 华北与华中连成一片
CORE_1938_06 = [[115.4, 40.1], [115.8, 40.4], [116.2, 40.9], [117.3, 40.6], [118.5, 40.2], [119.7, 40.1], [119.3, 39.3], [118.0, 39.0], [117.6, 38.5],
                [118.5, 38.0], [119.0, 37.3], [120.5, 37.8], [122.6, 37.4], [120.3, 36.0], [119.2, 35.0], [119.3, 34.6], [120.3, 34.3], [120.5, 33.4],
                [121.0, 32.6], [121.9, 31.7], [121.9, 30.85], [121.0, 30.6], [120.2, 30.2], [119.6, 30.5], [118.6, 30.9], [117.6, 30.6], [117.05, 30.45],
                [116.5, 30.5], [116.6, 31.2], [117.0, 32.0], [116.3, 33.0], [115.4, 33.6], [114.6, 34.3], [114.3, 34.8], [113.9, 35.3], [113.4, 35.4],
                [112.5, 35.0], [110.5, 35.0], [110.5, 36.5], [111.0, 37.5], [111.4, 38.6], [112.2, 38.9], [113.4, 39.3], [114.4, 39.6]]
# 1938-10：武汉会战后（武汉、信阳、岳阳）
CORE_1938_10 = CORE_1938_06[:28] + [[117.6, 30.6], [116.0, 29.7], [115.0, 29.8], [114.0, 29.4], [113.1, 29.3], [112.9, 30.0], [113.4, 30.9],
                                    [113.8, 31.7], [114.07, 32.12], [114.6, 32.4], [115.4, 33.6], [114.6, 34.3], [114.3, 34.8], [113.9, 35.3], [113.4, 35.4],
                                    [112.5, 35.0], [110.5, 35.0], [110.5, 36.5], [111.0, 37.5], [111.4, 38.6], [112.2, 38.9], [113.4, 39.3], [114.4, 39.6]]
# 1939-03 南昌；1940-06 宜昌 → 1939–1944 的大致稳定范围
CORE_1940 = CORE_1938_06[:28] + [[117.6, 30.6], [117.0, 29.6], [116.3, 28.8], [115.9, 28.4], [115.5, 28.7], [114.6, 29.0], [113.1, 29.3], [112.3, 29.8],
                                 [111.3, 30.6], [111.5, 31.1], [112.6, 31.0], [113.4, 30.9], [113.8, 31.7], [114.07, 32.12], [114.6, 32.4], [115.4, 33.6],
                                 [114.6, 34.3], [114.3, 34.8], [113.9, 35.3], [113.4, 35.4], [112.5, 35.0], [110.5, 35.0], [110.5, 36.5], [111.0, 37.5],
                                 [111.4, 38.6], [112.2, 38.9], [113.4, 39.3], [114.4, 39.6]]
# 1944 一号作战：豫中会战（郑州、洛阳）→ 长衡会战（长沙、衡阳）→ 桂柳会战（桂林、柳州、南宁），打通平汉、粤汉、湘桂线
HENAN_1944 = [[114.3, 34.8], [113.6, 34.75], [112.45, 34.65], [111.2, 34.75], [111.0, 34.2], [112.0, 33.6], [113.0, 33.1], [114.0, 32.6], [114.6, 32.4]]
HUNAN_1944 = [[113.1, 29.3], [112.6, 28.6], [112.9, 28.2], [112.6, 26.9], [113.0, 26.5], [113.7, 27.0], [113.5, 28.2], [114.0, 29.0]]
GUANGXI_1944 = [[112.6, 26.9], [111.0, 26.0], [110.3, 25.3], [109.4, 24.3], [108.3, 22.8], [107.0, 22.0], [107.4, 21.7], [108.5, 22.2], [109.2, 23.4],
                [110.4, 24.2], [111.6, 25.0], [113.0, 26.5]]
CANTON = [[113.0, 23.4], [113.6, 23.5], [114.2, 23.1], [114.1, 22.56], [113.6, 22.5], [113.0, 22.8]]
SHANTOU = [[116.4, 23.2], [116.4, 23.6], [117.0, 23.6], [117.0, 23.2]]
XIAMEN = [[117.95, 24.35], [117.95, 24.6], [118.25, 24.6], [118.25, 24.35]]
HAINAN = {"admin1": ["CN-HI"], "intersect_bbox": [108.5, 18.0, 111.2, 20.2]}

MANCHURIA = {"basemap": {"snap": 1930, "name": "Manchuria"}}
JEHOL = [[116.4, 41.0], [117.4, 40.6], [118.5, 40.2], [119.7, 40.1], [120.4, 40.6], [121.6, 41.5], [121.0, 42.6], [120.4, 43.5], [119.5, 44.6], [118.0, 44.8],
         [117.2, 44.0], [116.5, 43.0], [116.0, 42.0]]
EAST_HEBEI = [[116.6, 39.6], [116.9, 40.4], [117.5, 40.25], [118.5, 40.2], [119.6, 40.05], [119.4, 39.4], [118.6, 39.1], [117.8, 39.2], [117.2, 39.4]]
NORTH_CHAHAR = [[113.6, 41.5], [114.0, 42.8], [115.5, 43.5], [116.6, 44.5], [117.2, 44.0], [116.5, 43.0], [116.0, 42.0], [115.4, 41.4], [114.5, 41.2]]
MENGJIANG = [[109.6, 40.2], [109.6, 41.8], [111.0, 42.6], [111.9, 43.6], [113.0, 44.5], [114.5, 45.3], [116.5, 46.0], [117.8, 45.6], [117.5, 44.5], [117.2, 44.0],
             [116.5, 43.0], [116.0, 42.0], [116.2, 41.0], [115.8, 40.4], [115.4, 40.1], [114.4, 39.6], [113.4, 39.3], [112.2, 38.9], [111.5, 39.2], [111.0, 39.8],
             [110.4, 40.1]]
NORTH_BOX = [[100.0, 34.3], [100.0, 42.5], [125.0, 42.5], [125.0, 34.3]]
SOUTH_BOX = [[100.0, 17.0], [100.0, 34.3], [125.0, 34.3], [125.0, 17.0]]
EAST_BOX = [[115.5, 28.0], [115.5, 34.3], [125.0, 34.3], [125.0, 28.0]]
SOUTH_NOT_EAST = [[100.0, 17.0], [100.0, 34.3], [115.5, 34.3], [115.5, 28.0], [125.0, 28.0], [125.0, 17.0]]   # 华中/华南框去掉维新政府辖区框

SJW_SRC = [USMA.format("Japanese Occupation, 1940"), USMA.format("Situation at the End of World War II"), WP + "Second_Sino-Japanese_War",
           WP + "Japanese-occupied_areas_of_China"]


def poly(p):
    return {"polygon": p}


def U(*specs):
    s = dict(specs[0])
    s["union"] = list(specs[1:])
    return s


def zone(id_, name_zh, name_en, qid, zh, frm, until, geom, kind="occupied", group="sino_japanese_war", note=None, dates_note=None, sources=None, approx=True):
    z = {"id": id_, "group": group, "kind": kind, "as_polity": True, "name_zh": name_zh, "name_en": name_en, "controller": {"qid": qid, "zh": zh},
         "from": frm, "until": until, "geometry": geom, "approx": approx, "sources": sources or SJW_SRC}
    if note:
        z["note"] = note
    if dates_note:
        z["dates_note"] = dates_note
    return z


Z = []
# ---- 九一八事变后的东北、伪满、热河 ----
Z.append(zone("sjw_manchuria_1931", "日本关东军占领区（中国东北）", "Kwantung Army-occupied Manchuria", "Q188712", "大日本帝国", "1931-09-19", "1932-03-01", MANCHURIA,
              dates_note="1931-09-18 九一八事变后关东军逐步占领东北：沈阳 09-19、吉林 09-21、齐齐哈尔 11-19、锦州 1932-01-03、哈尔滨 1932-02-05；1932-03-01 成立满洲国。",
              note="范围用 historical-basemaps 1930 年「Manchuria」多边形近似，按完成占领后的范围显示（其间各地失守日期不同）。",
              sources=[WP + "Japanese_invasion_of_Manchuria", WP + "Mukden_incident"]))
Z.append(zone("sjw_jehol_1933", "满洲国（热河省，1933 年 3 月起）", "Manchukuo (Jehol)", "Q30623", "满洲国", "1933-03-04", "1945-08-19", poly(JEHOL),
              dates_note="热河作战：日军与满洲国军 1933-02-23 进攻，03-04 承德失守，热河并入满洲国；1945-08 苏联对日作战后满洲国瓦解（溥仪 08-18 宣布退位）。",
              note="热河省范围为手绘近似（±50 km）。", sources=[WP + "Operation_Nekka", WP + "Rehe_Province"]))
Z.append(zone("sjw_east_hebei", "冀东防共自治政府", "East Hebei Autonomous Council", "Q707917", "冀东防共自治政府", "1935-11-25", "1938-02-01", poly(EAST_HEBEI),
              dates_note="1935-11-25 殷汝耕在通州成立「冀东防共自治委员会」（12 月改称政府），辖冀东 22 县；1938-02-01 并入中华民国临时政府。",
              note="22 县范围为手绘近似（长城以南、通州以东至山海关）。", sources=[WP + "East_Hebei_Autonomous_Council"]))
Z.append(zone("sjw_north_chahar", "蒙古军政府（察北）", "Mongol Military Government (North Chahar)", "Q85883982", "蒙古军政府", "1936-05-12", "1937-10-28", poly(NORTH_CHAHAR),
              dates_note="1935-06《秦土协定》后察哈尔北部由日本扶植的德王势力控制；1936-05-12 成立蒙古军政府；1937-10-28 改组为蒙古联盟自治政府。",
              note="察北范围为手绘近似（±80 km）。", sources=[WP + "Mengjiang", WP + "Qin–Doihara_Agreement"]))
Z.append(zone("sjw_mengjiang_1937", "蒙古联盟自治政府（日本扶植）", "Mongol United Autonomous Government", "Q11621245", "蒙古联盟自治政府", "1937-10-28", "1939-09-01", poly(MENGJIANG),
              dates_note="日军 1937-08/10 占领张家口、大同、归绥（呼和浩特）、包头；10-28 成立蒙古联盟自治政府（另有察南、晋北两自治政府，1937-11 组成蒙疆联合委员会），1939-09-01 合并为蒙疆联合自治政府。",
              note="范围为手绘近似：察哈尔、绥远（包头以东）与晋北大同一带；河套地区仍由傅作义部（国民革命军）控制。", sources=[WP + "Mengjiang"]))
Z.append(zone("sjw_mengjiang", "蒙疆联合自治政府（日本扶植）", "Mengjiang United Autonomous Government", "Q697837", "蒙疆联合自治政府", "1939-09-01", "1945-08-19", poly(MENGJIANG),
              dates_note="1939-09-01 成立，首都张家口；1945-08 苏蒙联军进攻后瓦解。", note="范围为手绘近似（±80 km）。", sources=[WP + "Mengjiang"]))

# ---- 关内日占区 + 傀儡政权（按阶梯节点 × 政权时期求交） ----
JSTEPS = [  # (from, until, 几何规格, 节点说明, 来源)
    ("1937-08-15", "1937-11-12", poly(NORTH_1937), "1937-08 至 11 上旬：平津（07-29/30）、保定（09-24）、石家庄（10-10）、德州（10-03）", [WP + "Battle_of_Beiping–Tianjin", WP + "Battle_of_Taiyuan"]),
    ("1937-11-12", "1938-06-06", U(poly(NORTH_1938), poly(LOWER_YANGTZE_1937)),
     "1937-11 至 1938-05：太原（11-08）、上海（11-12）、南京（12-13）、杭州（12-24）、济南（12-27）、青岛（1938-01-10）、徐州（05-19）", [WP + "Battle_of_Shanghai", WP + "Battle_of_Nanking", WP + "Battle_of_Xuzhou"]),
    ("1938-06-06", "1938-10-21", poly(CORE_1938_06), "1938-06 至 10：开封（06-06）、安庆（06-12）、九江（07-26），津浦线贯通", [WP + "Battle_of_Xuzhou", WP + "Battle_of_Wuhan"]),
    ("1938-10-21", "1939-03-27", U(poly(CORE_1938_10), poly(CANTON), poly(XIAMEN)), "1938-10 至 1939-03：广州（10-21）、武汉（10-25）、岳阳（11-11）；厦门（1938-05）",
     [WP + "Battle_of_Wuhan", WP + "Canton_Operation", WP + "Battle_of_Amoy"]),
    ("1939-03-27", "1944-04-19", U(poly(CORE_1940), poly(CANTON), poly(XIAMEN), poly(SHANTOU), HAINAN),
     "1939-03 至 1944-04 的大致稳定范围：南昌（1939-03-27）、海南岛（1939-02-10）、汕头（1939-06-21）、宜昌（1940-06-12）；南宁 1939-11 至 1940-10、福州 1941-04 至 09 等短期占领未画",
     [WP + "Battle_of_Nanchang", WP + "Japanese_invasion_of_Hainan_Island", WP + "Battle_of_Zaoyang–Yichang", USMA.format("Japanese Occupation, 1940")]),
    ("1944-04-19", "1944-08-08", U(poly(CORE_1940), poly(HENAN_1944), poly(CANTON), poly(XIAMEN), poly(SHANTOU), HAINAN),
     "1944-04 至 08：一号作战第一阶段（豫中会战：郑州 04-22、洛阳 05-25），平汉线贯通；长沙 06-18 失守、衡阳 08-08 失守", [WP + "Operation_Ichi-Go", WP + "Battle_of_Central_Henan"]),
    ("1944-08-08", "1944-11-10", U(poly(CORE_1940), poly(HENAN_1944), poly(HUNAN_1944), poly(CANTON), poly(XIAMEN), poly(SHANTOU), HAINAN),
     "1944-08 至 11：长衡会战后粤汉线北段（长沙、衡阳）", [WP + "Operation_Ichi-Go", WP + "Battle_of_Changsha_(1944)", WP + "Defense_of_Hengyang"]),
    ("1944-11-10", "1945-08-16", U(poly(CORE_1940), poly(HENAN_1944), poly(HUNAN_1944), poly(CANTON), poly(XIAMEN), poly(SHANTOU), HAINAN),
     "1944-11 至 1945-08：桂柳会战的广西走廊另见 sjw_ichigo_guangxi（日军军事占领，不是汪政权行政区域）",
     [WP + "Operation_Ichi-Go", WP + "Battle_of_Guilin–Liuzhou", USMA.format("Situation at the End of World War II")]),
]
REGIMES = [  # (from, until, 区域框, QID, 名称, 说明, 来源)
    ("1937-07-07", "1937-12-14", NORTH_BOX, "Q188712", "日军占领区（华北）", "日军直接军事管制（1937-12-14 成立中华民国临时政府）", []),
    ("1937-12-14", "1940-03-30", NORTH_BOX, "Q704714", "中华民国临时政府（北平，日本扶植）", "1937-12-14 王克敏在北平成立，1940-03-30 并入汪精卫政权（改称华北政务委员会）", [WP + "Provisional_Government_of_the_Republic_of_China_(1937–1940)"]),
    ("1940-03-30", "1945-08-16", NORTH_BOX, "Q10905486", "华北政务委员会（汪精卫政权辖下，日军控制）", "名义上隶属南京汪精卫政权，实际自治并受日军华北方面军控制", [WP + "North_China_Political_Council"]),
    ("1937-07-07", "1938-03-28", SOUTH_BOX, "Q188712", "日军占领区（华中/华南）", "日军直接军事管制（上海另有「大道市政府」等地方伪组织）", []),
    ("1938-03-28", "1940-03-30", EAST_BOX, "Q708865", "中华民国维新政府（南京，日本扶植）", "1938-03-28 梁鸿志在南京成立，辖苏、浙、皖日占区；1940-03-30 并入汪精卫政权", [WP + "Reformed_Government_of_the_Republic_of_China"]),
    ("1938-03-28", "1940-03-30", SOUTH_NOT_EAST, "Q188712", "日军占领区（华中/华南）", "武汉、广州等地由日军直接管制", []),
    ("1940-03-30", "1945-08-16", SOUTH_BOX, "Q696242", "汪精卫政权（「中华民国国民政府」，南京，日本扶植）", "1940-03-30 汪精卫在南京成立，1944-11 汪死后由陈公博代理，1945-08-16 宣布解散", [WP + "Wang_Jingwei_regime"]),
]


def d2i(s):
    return int(s.replace("-", ""))


for jf, ju, jg, jlab, jsrc in JSTEPS:
    for rf, ru, box, q, zh, rnote, rsrc in REGIMES:
        a, b = max(jf, rf), min(ju, ru)
        if d2i(a) >= d2i(b):
            continue
        g = dict(jg)
        g = {"polygon": box, "intersect": jg}
        Z.append(zone(f"sjw_{q}_{a}_{REGIMES.index((rf, ru, box, q, zh, rnote, rsrc))}", zh, zh, q, zh.split("（")[0], a, b, g,
                      dates_note=f"日占区节点：{jlab}。政权：{rnote}。",
                      note="日军实际控制的是城市与铁路沿线（「点和线」），乡村多为国民革命军游击区与共军敌后根据地；色块为大致范围（±50–150 km）。",
                      sources=SJW_SRC + jsrc + rsrc))

# 桂柳会战走廊：日军军事占领，不是汪精卫政权的省政。
# 桂林 1944-11-10、柳州 11-11、南宁 11-24 失守。1945-05 起日军撤出的逐城日期不在这一块里细分。
# https://en.wikipedia.org/wiki/Battle_of_Guilin–Liuzhou
# https://en.wikipedia.org/wiki/Operation_Ichi-Go
# https://zh.wikipedia.org/wiki/桂柳会战
Z.append(zone("sjw_ichigo_guangxi", "日军军事占领区（桂柳会战）", "Japanese military occupation during the Battle of Guilin–Liuzhou",
              "Q188712", "大日本帝国", "1944-11-10", "1945-08-16", poly(GUANGXI_1944),
              dates_note="桂柳会战：1944-11-10 桂林、11-11 柳州、11-24 南宁失守，由日军军事占领，不是汪精卫政权的行政区域。1945-05 起日军自广西逐步撤出（南宁 05-26、柳州 06-30、桂林 07-28 被国民革命军收复），逐城撤退未再细分。",
              note="色块为桂柳走廊的大致范围（±50–150 km），不是省界，也不表示乡村全部被占领。",
              sources=[WP + "Battle_of_Guilin–Liuzhou", WP + "Operation_Ichi-Go", ZWP + "桂柳会战",
                       USMA.format("Situation at the End of World War II")]))

# ---- 共军根据地（大致范围，叠加在日占区之上） ----
SGN = [[106.9, 35.3], [106.5, 36.2], [106.9, 37.0], [107.3, 37.9], [108.0, 37.6], [109.0, 37.6], [109.5, 38.0], [110.6, 38.0], [110.6, 37.3], [110.4, 36.4],
       [110.0, 35.8], [109.2, 35.6], [108.6, 35.2], [107.7, 34.9]]
JCJ = [[113.0, 38.2], [113.3, 39.2], [114.2, 39.7], [115.3, 39.9], [115.6, 39.4], [115.0, 38.9], [114.6, 38.4], [114.0, 38.0], [113.4, 37.9]]
JJLY = [[112.6, 36.0], [112.8, 37.3], [113.5, 37.8], [114.0, 37.6], [114.1, 36.8], [113.9, 36.0], [113.4, 35.5], [112.8, 35.5]]
JS = [[110.6, 38.0], [110.9, 39.4], [111.6, 39.6], [112.2, 38.9], [112.0, 38.0], [111.6, 37.3], [111.0, 37.2], [110.6, 37.3]]
CCP_NOTE = "共军根据地（中共领导的边区政府）的范围随战事不断变化，这里只按核心山区画出大致范围（粗略，±100 km），不代表边界。"
Z.append(zone("sjw_ccp_sgn", "陕甘宁边区（中共根据地，大致范围）", "Shaan-Gan-Ning Border Region", "Q5970542", "陕甘宁边区", "1937-09-06", "1947-03-19", poly(SGN), kind="de_facto",
              dates_note="1937-09-06 陕甘宁边区政府成立（首府延安）；1947-03-19 国民革命军胡宗南部攻占延安（1948-04 共军收复，未画）。", note=CCP_NOTE,
              sources=[WP + "Shaan-Gan-Ning_Border_Region", ZWP + "陕甘宁边区"]))
Z.append(zone("sjw_ccp_jcj", "晋察冀边区（中共根据地，大致范围）", "Jin-Cha-Ji Border Region", "Q11089353", "晋察冀边区", "1938-01-10", "1945-08-16", poly(JCJ), kind="de_facto",
              dates_note="1938-01-10 晋察冀边区临时行政委员会在阜平成立，核心为五台山—太行山北段。", note=CCP_NOTE, sources=[WP + "Jin-Cha-Ji_Border_Region", ZWP + "晋察冀边区"]))
Z.append(zone("sjw_ccp_jjly", "晋冀鲁豫边区（中共根据地，大致范围）", "Jin-Ji-Lu-Yu Border Region", "Q11089315", "晋冀鲁豫边区", "1941-07-07", "1945-08-16", poly(JJLY), kind="de_facto",
              dates_note="以太行山南段为核心的根据地 1937–38 年形成，1941-07-07 晋冀鲁豫边区政府成立。", note=CCP_NOTE + "（只画太行山区，冀南、冀鲁豫平原部分未画。）",
              sources=[ZWP + "晋冀鲁豫边区"]))
Z.append(zone("sjw_ccp_js", "晋绥边区（中共根据地，大致范围）", "Jin-Sui Border Region", "Q24841584", "晋绥边区", "1940-02-01", "1945-08-16", poly(JS), kind="de_facto",
              dates_note="1940 年初晋西北行政公署成立（1943 年改称晋绥边区），核心为晋西北兴县一带。", note=CCP_NOTE, sources=[ZWP + "晋绥边区"]))

# ---- 1945-08 后的东北 ----
Z.append(zone("ccw_soviet_manchuria", "苏军占领下的中国东北", "Soviet-occupied Manchuria", "Q15132619", "苏联红军（东北）", "1945-08-19", "1946-05-03", U(MANCHURIA, poly(JEHOL)),
              group="ccw_manchuria", dates_note="苏联 1945-08-09 对日作战，08-19 前后占领东北各大城市；按《中苏友好同盟条约》应于 3 个月内撤军，实际 1946-05-03 撤完。",
              note="范围为 1930 年快照的东北 + 热河（近似）。", sources=[WP + "Soviet_occupation_of_Manchuria", WP + "Soviet_invasion_of_Manchuria"]))
NE_CCP_1946 = {"polygon": [[115.0, 53.6], [135.5, 53.6], [135.5, 42.9], [131.0, 42.9], [129.0, 43.0], [127.5, 43.5], [126.6, 44.4], [125.8, 44.6], [124.0, 45.4], [119.0, 46.5], [115.0, 47.0]],
               "intersect": MANCHURIA}
ROC_CORRIDOR_1947 = [[119.8, 40.1], [121.0, 40.6], [121.3, 41.3], [122.0, 41.6], [123.0, 42.0], [123.85, 42.4], [124.35, 43.3], [125.3, 44.0], [126.55, 44.0],
                     [126.7, 43.7], [125.5, 43.6], [124.6, 43.0], [124.1, 42.1], [123.5, 41.4], [123.3, 40.6], [122.3, 40.3], [121.5, 40.0], [120.5, 39.8]]
ROC_1948 = [[119.8, 40.1], [121.0, 40.6], [121.3, 41.3], [122.0, 41.6], [123.0, 42.0], [123.7, 42.1], [123.6, 41.5], [123.3, 40.9], [122.3, 40.4], [121.5, 40.0], [120.5, 39.8]]
CHANGCHUN = [[125.1, 43.75], [125.1, 44.05], [125.5, 44.05], [125.5, 43.75]]
Z.append(zone("ccw_ne_ccp_1946", "东北解放区（共军控制，大致范围）", "CCP-held northern Manchuria", "Q97179246", "东北行政委员会", "1946-06-07", "1947-05-13", NE_CCP_1946,
              kind="de_facto", group="ccw_manchuria",
              dates_note="苏军撤出后国共争夺东北；1946-06-07 东北停战令后大致以松花江为界：共军控制哈尔滨（1946-04-28 进入）及松花江以北、吉林东部，国民革命军控制长春、沈阳及南满；1946-08 东北各省市行政联合办事处成立（后称东北行政委员会）。",
              note="以松花江为界的手绘近似（±100 km）；国民革命军控制区仍显示为「中华民国」。", sources=[WP + "Chinese_Civil_War", WP + "Siping_campaign", ZWP + "东北行政委员会_(1946年—1949年)"]))
Z.append(zone("ccw_ne_ccp_1947", "东北解放区（共军控制，大致范围）", "CCP-held Manchuria", "Q97179246", "东北行政委员会", "1947-05-13", "1948-03-13",
              {"basemap": {"snap": 1930, "name": "Manchuria"}, "minus": {"polygon": ROC_CORRIDOR_1947}}, kind="de_facto", group="ccw_manchuria",
              dates_note="1947 年夏季、秋季、冬季攻势后，国民革命军只控制北宁、中长铁路沿线的长春—四平—沈阳—锦州走廊（四平 1948-03-13 失守）。",
              note="国民革命军控制走廊为沿铁路的手绘近似（宽约 50–100 km）。", sources=[WP + "Chinese_Civil_War", WP + "Liaoshen_campaign"]))
Z.append(zone("ccw_ne_ccp_1948", "东北解放区（共军控制，大致范围）", "CCP-held Manchuria", "Q97179246", "东北行政委员会", "1948-03-13", "1948-11-02",
              {"basemap": {"snap": 1930, "name": "Manchuria"}, "minus": {"polygon": ROC_1948, "union": [{"polygon": CHANGCHUN}]}}, kind="de_facto", group="ccw_manchuria",
              dates_note="1948-03 后国民革命军只剩被围的长春（1948-10-19 投降）与沈阳—锦州走廊；辽沈战役锦州 10-15、沈阳 11-02 失守，东北全境由共军控制。",
              sources=[WP + "Liaoshen_campaign", WP + "Siege_of_Changchun"]))
Z.append(zone("ccw_ne_ccp_1948b", "东北解放区（共军控制）", "CCP-held Manchuria", "Q97179246", "东北行政委员会", "1948-11-02", "1949-10-01", MANCHURIA, kind="de_facto", group="ccw_manchuria",
              dates_note="辽沈战役结束（1948-11-02）至中华人民共和国成立（1949-10-01；东北人民政府 1949-08 成立）。", sources=[WP + "Liaoshen_campaign"]))

# ---- 太平洋战争：东南亚日占区 ----
PAC = [WP + "Japanese_occupation_of_Southeast_Asia" if False else WP + "Greater_East_Asia_Co-Prosperity_Sphere", WP + "Pacific_War"]


def cs(gws, date):
    return {"cshapes": {"gw": gws, "date": date}}


Z += [
    zone("pac_hk", "日占香港", "Japanese occupation of Hong Kong", "Q701967", "日占香港", "1941-12-25", "1945-08-30", {"admin0_parts": {"a3": ["HKG"], "bbox": [113.8, 22.1, 114.5, 22.6]}},
         group="ww2_asia", approx=False, dates_note="1941-12-25「黑色圣诞」港督杨慕琦投降；1945-08-30 英国海军夏悫少将抵港接收。", sources=[WP + "Japanese_occupation_of_Hong_Kong"]),
    zone("pac_malaya", "日占马来亚", "Japanese occupation of Malaya", "Q713768", "日占马来亚", "1942-01-31", "1945-09-12", U(cs([821, 822], "1942-01-01"), {"admin0_parts": {"a3": ["MYS"], "bbox": [99.5, 1.2, 104.6, 6.8], "max_area": 20}}),
         group="ww2_asia", dates_note="日军 1941-12-08 在哥打巴鲁登陆，1942-01-31 占领马来半岛全境（柔佛）；1945-09-12 新加坡受降，英国恢复统治（英军军政府）。",
         note="边界取 CShapes 1942 年马来联邦/马来属邦范围。", sources=[WP + "Japanese_occupation_of_Malaya", WP + "Malayan_campaign"]),
    zone("pac_singapore", "昭南岛（日占新加坡）", "Japanese occupation of Singapore", "Q715645", "日占新加坡", "1942-02-15", "1945-09-12", {"admin0_parts": {"a3": ["SGP"], "bbox": [103.5, 1.1, 104.2, 1.5]}},
         group="ww2_asia", approx=False, dates_note="1942-02-15 英军白思华中将投降；1945-09-12 日军在新加坡市政厅向蒙巴顿投降。", sources=[WP + "Japanese_occupation_of_Singapore", WP + "Fall_of_Singapore"]),
    zone("pac_borneo", "日占英属婆罗洲", "Japanese occupation of British Borneo", "Q15243087", "日占英属婆罗洲", "1942-01-19", "1945-09-10", cs([823, 824, 835], "1942-01-01"),
         group="ww2_asia", dates_note="日军 1941-12-16 登陆，古晋 12-24、北婆罗洲首府 1942-01-19 失守；1945-06 起澳军登陆，1945-09-10 日军投降。",
         sources=[WP + "Japanese_occupation_of_British_Borneo"]),
    zone("pac_dei", "日占荷属东印度", "Japanese occupation of the Dutch East Indies", "Q702310", "日占荷属东印度", "1942-03-09", "1945-08-17", cs([850], "1942-01-01"),
         group="ww2_asia", dates_note="荷属东印度军 1942-03-08/09 在爪哇投降；1945-08-15 日本投降，08-17 苏加诺宣布印度尼西亚独立。",
         note="荷属新几内亚南部（梅劳克等）始终未被占领，这里整片显示（近似）。", sources=[WP + "Japanese_occupation_of_the_Dutch_East_Indies", WP + "Dutch_East_Indies_campaign"]),
    zone("pac_philippines", "日占菲律宾", "Japanese occupation of the Philippines", "Q3175954", "日占菲律宾", "1942-05-06", "1945-07-05", cs([840], "1942-01-01"),
         group="ww2_asia", dates_note="科雷希多 1942-05-06 投降；第二菲律宾共和国（日本扶植）1943-10-14 成立；美军 1944-10-20 莱特岛登陆、1945-03-03 收复马尼拉，1945-07-05 麦克阿瑟宣布菲律宾解放（山区日军抵抗至 08-15 后）。",
         note="1944-10 至 1945-07 美军逐岛收复，这里未逐岛细分（近似）。", sources=[WP + "Japanese_occupation_of_the_Philippines", WP + "Philippines_campaign_(1944–1945)"]),
    zone("pac_burma", "日占缅甸", "Japanese occupation of Burma", "Q1521499", "日占缅甸", "1942-05-20", "1943-08-01", cs([775], "1942-01-01"),
         group="ww2_asia", dates_note="1942-03-08 仰光、05-01 曼德勒失守，05-20 前后英军撤入印度；1943-08-01 成立日本扶植的「缅甸国」。", sources=[WP + "Japanese_occupation_of_Burma", WP + "Burma_campaign"]),
    zone("pac_burma_state", "缅甸国（日本扶植）", "State of Burma", "Q704358", "缅甸国", "1943-08-01", "1945-05-03", cs([775], "1942-01-01"),
         group="ww2_asia", dates_note="巴莫政府 1943-08-01 成立；1944–45 年盟军反攻（密支那 1944-08-03、曼德勒 1945-03-20），1945-05-03 收复仰光。",
         note="1944–45 年缅北已逐步被盟军收复，这里未细分（近似）。", sources=[WP + "State_of_Burma", WP + "Burma_campaign"]),
    zone("pac_indochina", "法属印度支那（维希法国管治，日军进驻）", "French Indochina under Japanese occupation", "Q362078", "二战中的法属印度支那", "1941-07-28", "1945-03-09", cs([811, 812, 815], "1942-01-01"),
         group="ww2_asia", dates_note="日军 1940-09-22 进驻北部（东京），1941-07-28 进驻南部；法国维希政府的总督府继续行政管理，直到 1945-03-09 日军发动「明号作战」政变。",
         sources=[WP + "French_Indochina_in_World_War_II", WP + "Japanese_invasion_of_French_Indochina"]),
    zone("pac_vietnam_empire", "越南帝国（日本扶植）", "Empire of Vietnam", "Q701337", "越南帝国", "1945-03-11", "1945-08-25", cs([815], "1942-01-01"),
         group="ww2_asia", dates_note="保大帝 1945-03-11 宣布独立；1945-08-25 退位（八月革命）。", sources=[WP + "Empire_of_Vietnam"]),
    zone("pac_kampuchea", "柬埔寨王国（日本扶植）", "Kingdom of Kampuchea (1945)", "Q16673775", "柬埔寨王国 (1945年)", "1945-03-13", "1945-10-16", cs([811], "1942-01-01"),
         group="ww2_asia", dates_note="西哈努克 1945-03-13 宣布独立；1945-10-16 法国恢复控制。", sources=[WP + "Kingdom_of_Kampuchea_(1945)"]),
    zone("pac_laos", "日军控制下的老挝（琅勃拉邦王国）", "Laos under Japanese control", "Q338248", "琅勃拉邦王国", "1945-03-09", "1945-08-30", cs([812], "1942-01-01"),
         group="ww2_asia", dates_note="日军 1945-03-09 政变后控制老挝，西萨旺冯国王 04-08 宣布独立；日本投降后 1945-08-30 前后失效。", sources=[WP + "French_Indochina_in_World_War_II"]),
    zone("pac_timor", "日占帝汶", "Japanese occupation of Timor", "Q188712", "大日本帝国", "1942-02-20", "1945-09-11", U(cs([860], "1942-01-01"), {"admin0_parts": {"a3": ["TLS"], "bbox": [124.0, -9.6, 127.5, -8.1]}}),
         group="ww2_asia", dates_note="日军 1942-02-19/20 登陆帝汶；1945-09-11 帝汶日军在古邦向澳军投降（荷属西帝汶已包含在荷属东印度中）。", sources=[WP + "Battle_of_Timor"]),
    zone("pac_andaman", "日占安达曼和尼科巴群岛", "Japanese occupation of the Andaman and Nicobar Islands", "Q4065239", "日占安达曼和尼科巴群岛", "1942-03-23", "1945-10-09", {"admin1": ["IN-AN"]},
         group="ww2_asia", approx=False, dates_note="日军 1942-03-23 占领布莱尔港；1945-10-09 日军投降。", sources=[WP + "Japanese_occupation_of_the_Andaman_and_Nicobar_Islands"]),
    zone("pac_guam", "日占关岛", "Japanese occupation of Guam", "Q6158903", "日占关岛", "1941-12-10", "1944-08-10", {"admin0_parts": {"a3": ["GUM"], "bbox": [144.5, 13.2, 145.0, 13.7]}},
         group="ww2_asia", approx=False, dates_note="1941-12-10 美军守备队投降；1944-07-21 美军登陆，08-10 收复。", sources=[WP + "Japanese_occupation_of_Guam"]),
    zone("pac_nauru", "日占瑙鲁", "Japanese occupation of Nauru", "Q2072172", "日占瑙鲁", "1942-08-26", "1945-09-13", {"admin0_parts": {"a3": ["NRU"], "bbox": [166.8, -0.6, 167.0, -0.45]}},
         group="ww2_asia", approx=False, dates_note="日军 1942-08-26 登陆；1945-09-13 向澳军投降。", sources=[WP + "Japanese_occupation_of_Nauru"]),
    zone("pac_gilberts", "日占吉尔伯特群岛", "Japanese occupation of the Gilbert Islands", "Q65270011", "日占吉尔伯特群岛", "1941-12-10", "1943-11-23", {"admin0_parts": {"a3": ["KIR"], "bbox": [172.0, -3.0, 177.5, 4.0]}},
         group="ww2_asia", dates_note="日军 1941-12-10 占领马金、塔拉瓦；1943-11-20/23 美军攻占塔拉瓦、马金。", sources=[WP + "Japanese_occupation_of_the_Gilbert_Islands"]),
]

cur = json.loads(P.read_text(encoding="utf-8"))
cur["zones"] = [z for z in cur["zones"] if z.get("group") not in GROUPS] + Z
doc = cur["_doc"]
extra = "geometry 另可用 cshapes {gw:[…], date}（CShapes 2.0 该日期有效的行）与 intersect（与另一几何规格求交）。"
if extra not in doc:
    doc.append(extra)
P.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
print("zones written:", len(Z), "total", len(cur["zones"]))
