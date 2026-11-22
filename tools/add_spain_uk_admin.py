"""补西班牙普查省和 1911 年英格兰、威尔士行政郡。

只追加到已有的 europe_admin.geojson。没有这两份文件时不改原文件。
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pyogrio
from pyproj import Transformer
from shapely import wkb
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform, unary_union

from build_europe_admin import clean_geom, dump_geom

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "geom" / "europe_admin.geojson"
SPAIN = Path("/tmp/euadm/gap/spain.topojson.gz")
UK = Path("/tmp/euadm/gap/EW1911_admcounties.shp")

ES = {
    "Albacete": "阿尔瓦塞特", "Alicante/Alacant": "阿利坎特", "Almería": "阿尔梅里亚",
    "Araba/Álava": "阿拉瓦", "Avila": "阿维拉", "Badajoz": "巴达霍斯",
    "Balears (Illes)": "巴利阿里", "Barcelona": "巴塞罗那", "Bizkaia": "比斯开",
    "Burgos": "布尔戈斯", "Castellón/Castelló": "卡斯特利翁", "Ciudad Real": "雷阿尔城",
    "Coruña (A)": "拉科鲁尼亚", "Cuenca": "昆卡", "Cáceres": "卡塞雷斯", "Cádiz": "加的斯",
    "Córdoba": "科尔多瓦", "Gipuzkoa": "吉普斯夸", "Girona": "赫罗纳", "Granada": "格拉纳达",
    "Guadalajara": "瓜达拉哈拉", "Huelva": "韦尔瓦", "Huesca": "韦斯卡", "Jaén": "哈恩",
    "León": "莱昂", "Lleida": "莱里达", "Lugo": "卢戈", "Madrid": "马德里", "Murcia": "穆尔西亚",
    "Málaga": "马拉加", "Navarra": "纳瓦拉", "Ourense": "奥伦塞", "Palencia": "帕伦西亚",
    "Pontevedra": "蓬特韦德拉", "Salamanca": "萨拉曼卡", "Segovia": "塞戈维亚",
    "Sevilla": "塞维利亚", "Soria": "索里亚", "Tarragona": "塔拉戈纳", "Teruel": "特鲁埃尔",
    "Toledo": "托莱多", "Valencia/València": "巴伦西亚", "Valladolid": "巴利亚多利德",
    "Zamora": "萨莫拉", "Zaragoza": "萨拉戈萨",
    "Palmas (Las)": "拉斯帕尔马斯", "Santa Cruz de Tenerife": "圣克鲁斯-德特内里费",
}
UKN = {
    "ANGLESEY": "安格尔西", "BEDFORDSHIRE": "贝德福德", "BERKSHIRE": "伯克",
    "BRECKNOCKSHIRE": "布雷克诺克", "BUCKINGHAMSHIRE": "白金汉", "CAERNARVONSHIRE": "卡那封",
    "CAMBRIDGESHIRE": "剑桥", "CARDIGANSHIRE": "卡迪根", "CARMARTHENSHIRE": "卡马森",
    "CHESHIRE": "柴郡", "CORNWALL": "康沃尔", "COUNTY DURHAM": "达勒姆", "CUMBERLAND": "坎伯兰",
    "DENBIGHSHIRE": "登比", "DERBYSHIRE": "德比", "DEVON": "德文", "DORSET": "多塞特",
    "EAST RIDING": "约克东区", "EAST SUFFOLK": "东萨福克", "EAST SUSSEX": "东萨塞克斯",
    "ESSEX": "埃塞克斯", "FLINTSHIRE": "弗林特", "GLAMORGAN": "格拉摩根",
    "GLOUCESTERSHIRE": "格洛斯特", "HAMPSHIRE": "汉普", "HEREFORDSHIRE": "赫里福德",
    "HERTFORDSHIRE": "赫特福德", "HUNTINGDONSHIRE": "亨廷登", "ISLE OF ELY": "伊利岛",
    "ISLE OF WIGHT": "怀特岛", "KENT": "肯特", "LANCASHIRE": "兰开夏",
    "LEICESTERSHIRE": "莱斯特", "LONDON": "伦敦", "MERIONETHSHIRE": "梅里奥尼思",
    "MIDDLESEX": "米德尔塞克斯", "MONMOUTHSHIRE": "蒙茅斯", "MONTGOMERYSHIRE": "蒙哥马利",
    "NORFOLK": "诺福克", "NORTH RIDING": "约克北区", "NORTHAMPTONSHIRE": "北安普顿",
    "NORTHUMBERLAND": "诺森伯兰", "NOTTINGHAMSHIRE": "诺丁汉", "OXFORDSHIRE": "牛津",
    "PARTS OF HOLLAND": "荷兰诸区", "PARTS OF KESTEVEN": "凯斯蒂文诸区",
    "PARTS OF LINDSEY": "林赛诸区", "PEMBROKESHIRE": "彭布罗克", "RADNORSHIRE": "拉德诺",
    "RUTLAND": "拉特兰", "SHROPSHIRE": "什罗普", "SOKE OF PETERBOROUGH": "彼得伯勒辖区",
    "SOMERSET": "萨默塞特", "STAFFORDSHIRE": "斯塔福德", "SURREY": "萨里",
    "WARWICKSHIRE": "沃里克", "WEST RIDING": "约克西区", "WEST SUFFOLK": "西萨福克",
    "WEST SUSSEX": "西萨塞克斯", "WESTMORLAND": "威斯特摩兰", "WILTSHIRE": "威尔特",
    "WORCESTERSHIRE": "伍斯特",
}
CANARY = {"Palmas (Las)", "Santa Cruz de Tenerife"}
SKIP = {"Ceuta", "Melilla"}
NOTE_ES = (
    "Pau Vall-Prat，mapSpainHist，西班牙 1900–2001 年普查省，CC BY 4.0，"
    "https://doi.org/10.5281/zenodo.23663208 。由约 2000 年代初的市界按当年市镇归属归并，作者写明边界是近似。"
    "1900、1910、1920 年档把拉斯帕尔马斯和圣克鲁斯-德特内里费并成一个加那利省，到 1927-09-21 为止。"
    "这一天起用 1930 年档里分开的两省。休达和梅利利亚不是省，不画。"
    "桑坦德、洛格罗尼奥、奥维耶多在 1981 年档起改用后来的省名，改名法令的日子没有另切。"
    "2001 年档收到 2011-11-01。1833 年至 1899 年没有这套几何。"
)
NOTE_UK = (
    "Great Britain Historical GIS，1911 年英格兰和威尔士行政郡，CC BY-SA 4.0，"
    "https://purl.stanford.edu/wb643sv2814 。这是 1889 年地方政府法之后、1974 年以前的行政郡在 1911 年普查时的样子。"
    "只从 1911-04-02 用到 1921-06-19。1889 年至这次普查前、以及 1921 年普查以后，没有这套几何。"
    "郡级市没有单独切开。苏格兰和爱尔兰不在这份文件里。按 CC BY-SA 4.0 再分发。"
)


def arc_line(arcs, index):
    if index < 0:
        return list(reversed(arcs[~index]))
    return list(arcs[index])


def topo_geom(arcs, geom):
    def ring(indices):
        points = []
        for index in indices:
            segment = arc_line(arcs, index)
            if points:
                segment = segment[1:]
            points.extend(segment)
        if len(points) >= 2 and points[0] != points[-1]:
            points.append(points[0])
        return points

    kind = geom.get("type")
    coords = geom.get("arcs") or []
    if kind == "Polygon":
        rings = [ring(item) for item in coords if item]
        if not rings or len(rings[0]) < 4:
            return None
        return Polygon(rings[0], rings[1:])
    if kind == "MultiPolygon":
        polygons = []
        for part in coords:
            rings = [ring(item) for item in part if item]
            if rings and len(rings[0]) >= 4:
                polygons.append(Polygon(rings[0], rings[1:]))
        return MultiPolygon(polygons) if polygons else None
    return None


def es_label(nom, start):
    if nom == "Cantabria":
        return "桑坦德" if start < "1981-03-01" else "坎塔布里亚"
    if nom == "Rioja (La)":
        return "洛格罗尼奥" if start < "1981-03-01" else "拉里奥哈"
    if nom == "Asturias":
        return "奥维耶多" if start < "1981-03-01" else "阿斯图里亚斯"
    return ES[nom]


def add_feature(features, **prop):
    geom = prop.pop("geom")
    prop["id"] = f"{prop['source_id']}-{len(features)}"
    features.append({"type": "Feature", "properties": prop, "geometry": dump_geom(geom)})


def load_spain(features):
    data = json.load(gzip.open(SPAIN, "rt", encoding="utf-8"))
    arcs = data["arcs"]
    years = [1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1981, 1991, 2001]
    start_of = {
        1900: "1900-01-01", 1910: "1910-01-01", 1920: "1920-01-01", 1930: "1930-01-01",
        1940: "1940-01-01", 1950: "1950-01-01", 1960: "1960-01-01", 1970: "1970-01-01",
        1981: "1981-03-01", 1991: "1991-03-01", 2001: "2001-11-01",
    }
    end_of = {year: start_of[nxt] for year, nxt in zip(years, years[1:])}
    end_of[2001] = "2011-11-01"
    parsed = {}
    for year in years:
        parsed[year] = {}
        for geom in data["objects"][f"prov_hist_{year}"]["geometries"]:
            nom = geom["properties"]["nom"]
            if nom in SKIP:
                continue
            parsed[year][nom] = topo_geom(arcs, geom)
    url = "https://doi.org/10.5281/zenodo.23663208"
    for year in years:
        start, end = start_of[year], end_of[year]
        canary = []
        for nom, geom in parsed[year].items():
            if nom in CANARY and year <= 1920:
                if geom is not None:
                    canary.append(geom)
                continue
            if geom is None:
                continue
            cleaned = clean_geom(geom, 0.02)
            if cleaned is None:
                continue
            add_feature(
                features, name_src=nom, name=es_label(nom, start), kind="省", nominal="西班牙",
                source_id="es-census", license="CC BY 4.0", url=url, precision=NOTE_ES,
                **{"from": start, "until": end, "geom": cleaned},
            )
        if canary:
            merged = clean_geom(unary_union(canary), 0.02)
            until = "1927-09-21" if year == 1920 else end
            if merged is not None:
                add_feature(
                    features, name_src="Canarias", name="加那利", kind="省", nominal="西班牙",
                    source_id="es-census", license="CC BY 4.0", url=url, precision=NOTE_ES,
                    **{"from": start, "until": until, "geom": merged},
                )
    # 1927-09-21 至 1930-01-01 只用 1930 年档里已经分开的两个岛省。
    for nom in CANARY:
        geom = parsed[1930].get(nom)
        cleaned = clean_geom(geom, 0.02) if geom is not None else None
        if cleaned is None:
            continue
        add_feature(
            features, name_src=nom, name=es_label(nom, "1927-09-21"), kind="省", nominal="西班牙",
            source_id="es-census", license="CC BY 4.0", url=url, precision=NOTE_ES,
            **{"from": "1927-09-21", "until": "1930-01-01", "geom": cleaned},
        )


def load_uk(features):
    crs, = (pyogrio.read_info(UK)["crs"],)
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    _meta, table = pyogrio.read_arrow(UK, columns=["G_NAME"])
    names = table.column("G_NAME").to_pylist()
    blobs = table.column("wkb_geometry").to_pylist()
    url = "https://purl.stanford.edu/wb643sv2814"
    for label, blob in zip(names, blobs):
        geom = transform(transformer.transform, wkb.loads(bytes(blob)))
        cleaned = clean_geom(geom, 0.012)
        if cleaned is None:
            continue
        if label not in UKN:
            raise SystemExit(f"缺译名 {label}")
        add_feature(
            features, name_src=label, name=UKN[label], kind="行政郡", nominal="英国",
            source_id="gb-adm-1911", license="CC BY-SA 4.0", url=url, precision=NOTE_UK,
            **{"from": "1911-04-02", "until": "1921-06-19", "geom": cleaned},
        )


def main():
    data = json.loads(OUT.read_text(encoding="utf-8"))
    features = [feat for feat in data["features"] if feat["properties"].get("source_id") not in {"es-census", "gb-adm-1911"}]
    before = len(features)
    if SPAIN.exists():
        load_spain(features)
    if UK.exists():
        load_uk(features)
    gaps = [
        item for item in data.get("gaps") or []
        if "西班牙" not in item and "1889" not in item
    ]
    gaps.extend([
        "西班牙只收了 1900 年至 2011-11-01 的普查省。1833 年至 1899 年待考。休达和梅利利亚不画成省。",
        "英国 1889 年 4 月 1 日至 1911 年 4 月 2 日的行政郡、1921 年 6 月 19 日以后的行政郡，以及 1974 年的郡，待考。苏格兰和爱尔兰的行政郡待考。1911 年至 1921 年只有英格兰和威尔士。",
        "1871 年至 1918 年的巴伐利亚、符腾堡、巴登、萨克森王国，以及阿尔萨斯-洛林帝国领，HistoGIS 全文没有单独几何，待考。",
        "法国 1941 年以后的省界待考。罗马尼亚和南斯拉夫两次大战间的区划待考。",
    ])
    data["features"] = features
    data["gaps"] = gaps
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"features {before} -> {len(features)}")
    shapes = [(shape(feat["geometry"]), feat["properties"]) for feat in features if feat["properties"]["source_id"] in {"es-census", "gb-adm-1911"}]
    checks = [
        ("1930-06-01", -3.7038, 40.4168, "马德里"),
        ("1905-06-01", -3.7038, 40.4168, "马德里"),
        ("1880-06-01", -3.7038, 40.4168, None),
        ("1925-06-01", -16.2518, 28.4637, "加那利"),
        ("1930-06-01", -16.2518, 28.4637, "圣克鲁斯-德特内里费"),
        ("1912-06-01", -0.1278, 51.5074, "伦敦"),
        ("1905-06-01", -0.1278, 51.5074, None),
        ("1966-06-01", -0.1278, 51.5074, None),
        ("1912-06-01", -3.7038, 40.4168, "马德里"),
    ]
    for day, lon, lat, expect in checks:
        from shapely.geometry import Point
        point = Point(lon, lat)
        hits = []
        for geom, prop in shapes:
            if prop["from"] <= day < prop["until"] and geom.covers(point):
                hits.append((geom.area, prop["name"], prop["name_src"]))
        hits.sort()
        got = hits[0][1] if hits else None
        print(("OK" if got == expect else "DIFF"), day, "expect", expect, "got", got, hits[:2])


if __name__ == "__main__":
    main()
