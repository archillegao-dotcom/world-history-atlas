"""俄乌战争（2022 年全面入侵起）逐日俄控区 / 灰色区 → war_fronts 通用格式。

数据直接复用 /workspace/ukraine_front（同一作者的 OSINT 追踪器）已下载并处理好的真实数据，不做任何推测：
  - 2022-02-24 – 2022-04-02：ISW/CTP「Russian Assessed Control of Terrain」ArcGIS 图层的逐日评估控制区（无灰色区）；
  - 2022-04-03 起：DeepStateMap 公开历史快照（俄控区 = Occupied ∪ 克里米亚 ∪ 2014 年后占领区；灰色区 = 状态不明）。
  - 每天取欧洲/巴黎时间当天结束前的最后一个快照（ukraine_front/data/daily_metrics.csv 的 date → snapshot_id）。
另外加两条 2014–2022 的基线记录（克里米亚、2014 年后被占的顿涅茨克/卢甘斯克部分地区），几何取 DeepState 基线，标为近似。

输出：
  data/war_fronts/russo_ukrainian_war.json.gz  记录列表（字段与 data/curated/control_zones.json 相同 + dataset/snapshot/area_km2）
  data/war_fronts/russo_ukrainian_war/<snapshot>.json.gz  每个快照的几何 {"occupied": GeoJSON, "contested": GeoJSON}
增量：已存在的几何文件跳过。用法：.venv/bin/python tools/build_war_fronts_ukraine.py [--uf /workspace/ukraine_front]
"""
import csv, gzip, json, pickle, sys, datetime as dt
from pathlib import Path
import shapely
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
UF = Path(sys.argv[sys.argv.index("--uf") + 1]) if "--uf" in sys.argv else Path("/workspace/ukraine_front")
WAR = "russo_ukrainian_war"
OUT = ROOT / "data" / "war_fronts"
GEO = OUT / WAR
TOL = 0.001          # 约 100 m 的简化容差（地图显示用；面积仍取原始数据计算值）
RUSSIA = {"qid": "Q159", "zh": "俄罗斯"}
SRC_DS = "https://deepstatemap.live/"
SRC_ISW = "https://www.arcgis.com/home/item.html?id=963c5626435e49b98ae1db399859d04e"


def clean(g):
    if g is None or g.is_empty:
        return None
    g = make_valid(g)
    g = unary_union([p for p in getattr(g, "geoms", [g]) if p.geom_type in ("Polygon", "MultiPolygon")]) if g.geom_type == "GeometryCollection" else g
    g = shapely.set_precision(g.simplify(TOL, preserve_topology=True), 1e-4)
    return None if g.is_empty else mapping(g)


def ukraine_clip():
    gs = []
    for f in json.load(open(ROOT / "data/basemaps_raw/ne_10m_admin_0_countries.geojson"))["features"]:
        if f["properties"].get("ADM0_A3") == "UKR":
            gs.append(shape(f["geometry"]))
    for f in json.load(open(ROOT / "data/basemaps_raw/ne_10m_admin_1_states_provinces.geojson"))["features"]:
        if f["properties"].get("iso_3166_2") in ("UA-43", "UA-40"):     # 克里米亚、塞瓦斯托波尔（NE 默认归俄罗斯）
            gs.append(shape(f["geometry"]))
    return make_valid(unary_union(gs)).buffer(0.01)


def isw_by_date():
    fc = json.load(gzip.open(UF / "data/static/isw_cot_2022-02-24_2022-04-02.geojson.gz", "rt"))
    by = {}
    for f in fc["features"]:
        by.setdefault(f["properties"]["date"], []).append(make_valid(shape(f["geometry"])))
    return by


def main():
    GEO.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(UF / "data/daily_metrics.csv", encoding="utf-8")))
    clip, isw = None, None
    # 连续使用同一快照的日期合并为一条记录
    runs = []
    for r in rows:
        if runs and runs[-1]["sid"] == r["snapshot_id"]:
            runs[-1]["last"] = r["date"]
        else:
            runs.append({"sid": r["snapshot_id"], "first": r["date"], "last": r["date"], "row": r})
    recs, made = [], 0
    for i, run in enumerate(runs):
        sid, r = run["sid"], run["row"]
        f = GEO / f"{sid}.json.gz"
        if not f.exists():
            if int(sid) < 0:
                isw = isw or isw_by_date()
                clip = clip or ukraine_clip()
                d = dt.datetime.strptime(str(-int(sid)), "%Y%m%d").date().isoformat()
                occ, grey = unary_union(isw[d]).intersection(clip), None
            else:
                lay = pickle.loads((UF / f"data/layers_v4/{sid}.pkl").read_bytes())
                occ, grey = lay.get("occupied"), lay.get("grey")
            with gzip.open(f, "wt", encoding="utf-8") as fh:
                json.dump({"occupied": clean(occ), "contested": clean(grey)}, fh, separators=(",", ":"))
            made += 1
        nxt = runs[i + 1]["first"] if i + 1 < len(runs) else None
        isw_ = int(sid) < 0
        base = {"group": WAR, "from": run["first"], "until": nxt, "approx": False,
                "dataset": "isw_cot" if isw_ else "deepstate", "snapshot": sid,
                "snapshot_time": r["snapshot_time_paris"] + "（巴黎时间）",
                "geometry": {"file": f"{WAR}/{sid}.json.gz"},
                "sources": [SRC_ISW if isw_ else f"https://deepstatemap.live/#{sid}"]}
        recs.append({**base, "id": f"ua_occ_{sid}", "kind": "occupied", "controller": RUSSIA,
                     "name_zh": "俄军控制区", "name_en": "Russian-controlled territory",
                     "layer": "occupied", "area_km2": float(r["occupied_km2"] or 0)})
        if not isw_:
            recs.append({**base, "id": f"ua_grey_{sid}", "kind": "contested", "controller": None,
                         "name_zh": "灰色区（状态不明）", "name_en": "Grey zone (status unknown)",
                         "layer": "contested", "area_km2": float(r["grey_km2"] or 0)})
    # 2014–2022 基线（DeepState 基线几何：克里米亚、2015 年后的顿巴斯接触线以东）
    bl = json.load(open(UF / "data/static/deepstate_baseline_crimea_ordlo.geojson"))
    bf = GEO / "baseline_2014.json.gz"
    parts = {f["properties"]["kind"]: shape(f["geometry"]) for f in bl["features"]}
    with gzip.open(bf, "wt", encoding="utf-8") as fh:
        json.dump({"crimea": clean(parts["crimea"]), "ordlo": clean(parts["ordlo"])}, fh, separators=(",", ":"))
    recs.insert(0, {"id": "ua_crimea_2014", "group": WAR, "kind": "occupied", "controller": RUSSIA,
                    "name_zh": "克里米亚（俄罗斯 2014 年占领并宣布吞并）", "name_en": "Crimea (occupied and annexed by Russia, 2014)",
                    "from": "2014-03-18", "until": "2022-02-24", "approx": True, "dataset": "deepstate_baseline",
                    "geometry": {"file": f"{WAR}/baseline_2014.json.gz"}, "layer": "crimea",
                    "dates_note": "2014-02-27 起俄军夺取克里米亚要地，2014-03-18 俄罗斯宣布吞并（联合国大会第 68/262 号决议不承认）。2022-02-24 起见逐日数据。",
                    "sources": ["https://en.wikipedia.org/wiki/Annexation_of_Crimea_by_the_Russian_Federation", SRC_DS]})
    recs.insert(1, {"id": "ua_ordlo_2015", "group": WAR, "kind": "occupied", "controller": RUSSIA,
                    "name_zh": "顿涅茨克、卢甘斯克州部分地区（俄罗斯控制的「顿涅茨克/卢甘斯克人民共和国」）",
                    "name_en": "Russian-controlled parts of Donetsk and Luhansk oblasts",
                    "from": "2015-02-18", "until": "2022-02-24", "approx": True, "dataset": "deepstate_baseline",
                    "geometry": {"file": f"{WAR}/baseline_2014.json.gz"}, "layer": "ordlo",
                    "dates_note": "范围为 2015 年 2 月德巴尔采沃战役（2015-02-18 乌军撤出）后至 2022 年全面入侵前大体稳定的接触线；2014-04 至 2015-02 期间的变化没有逐日数据，不显示。",
                    "sources": ["https://en.wikipedia.org/wiki/Battle_of_Debaltseve", "https://en.wikipedia.org/wiki/Minsk_agreements", SRC_DS]})
    meta = {"id": WAR, "name_zh": "俄乌战争", "name_en": "Russo-Ukrainian War", "from": "2014-02-20",
            "belligerents": [{"qid": "Q159", "zh": "俄罗斯"}, {"qid": "Q212", "zh": "乌克兰"}],
            "data_until": rows[-1]["date"], "built": dt.datetime.now().isoformat(timespec="seconds"),
            "datasets": {
                "isw_cot": {"name": "ISW/CTP Russian Assessed Control of Terrain（ArcGIS）", "from": "2022-02-24", "until": "2022-04-03",
                            "url": SRC_ISW, "license": "© Institute for the Study of War & AEI Critical Threats Project（注明出处）",
                            "note": "评估控制区，无灰色区；与 DeepState 口径不同"},
                "deepstate": {"name": "DeepStateMap 公开历史快照", "from": "2022-04-03", "url": SRC_DS,
                              "license": "© DeepStateMap（公开数据，注明出处）",
                              "note": "每天取巴黎时间当天最后一个快照；俄控区含克里米亚与 2014 年后占领区；灰色区为状态不明，不计入俄控"},
                "deepstate_baseline": {"name": "DeepState 克里米亚 / 2014 年后占领区基线", "url": SRC_DS, "license": "© DeepStateMap",
                                       "note": "2014–2022 的近似范围"}},
            "method": "复用 /workspace/ukraine_front 的处理结果（tools/build_war_fronts_ukraine.py）；几何简化约 100 m，面积为原始数据在等积投影下的计算值。"}
    with gzip.open(OUT / f"{WAR}.json.gz", "wt", encoding="utf-8") as fh:
        json.dump({"war": meta, "zones": recs}, fh, ensure_ascii=False)
    print("runs", len(runs), "records", len(recs), "new geometry files", made, "data_until", meta["data_until"])


if __name__ == "__main__":
    main()
