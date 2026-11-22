"""补瑞典历史的省（län），1600–1990 年里有几何的那一段。

数据是 Johan Junkka 的 swehist 1.1.1，CC BY 4.0。
原始库在构建机的 /tmp/euadm/gap，不进仓库。
"""
from __future__ import annotations

import json
from pathlib import Path

import pyogrio
from pyproj import Transformer
from shapely import wkb
from shapely.ops import transform

from build_europe_admin import clean_geom, dump_geom

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "geom" / "europe_admin.geojson"
GPKG = Path("/tmp/euadm/gap/swehist-1.1.1-data/swehist.gpkg")
ZH = {
    "Stockholms län": "斯德哥尔摩", "Uppsala län": "乌普萨拉", "Södermanlands län": "南曼兰",
    "Östergötlands län": "东约特兰", "Jönköpings län": "延雪平", "Kronobergs län": "克鲁努贝里",
    "Kalmar län": "卡尔马", "Gotlands län": "哥特兰", "Blekinge län": "布莱金厄",
    "Kristianstads län": "克里斯蒂安斯塔德", "Malmöhus län": "马尔默胡斯", "Hallands län": "哈兰",
    "Göteborgs o Bohus län": "哥德堡-布胡斯", "Älvsborgs län": "埃尔夫斯堡", "Skaraborgs län": "斯卡拉堡",
    "Värmlands län": "韦姆兰", "Örebro län": "厄勒布鲁", "Västmanlands län": "西曼兰",
    "Kopparbergs län": "科帕尔贝里", "Gävleborgs län": "耶夫勒堡", "Västernorrlands län": "西诺尔兰",
    "Jämtlands län": "耶姆特兰", "Västerbottens län": "西博滕", "Norrbottens län": "北博滕",
    "Närke och Värmlands län": "内尔克-韦姆兰",
}
NOTE = (
    "Johan Junkka，swehist 1.1.1，瑞典历史省界，CC BY 4.0，"
    "https://doi.org/10.5281/zenodo.23396621 。省界由下级单元归并，不是当年的测绘原件。"
    "原表只有年份。从该年1月1日画到结束年的次年起，不是1月1日发生了变化。"
    "1990 年档收到 1991-01-01。斯德哥尔摩城的点不落在省多边形里，城本身待考。"
    "荷兰、比利时、挪威、丹麦、葡萄牙、匈牙利王国的州、捷克斯洛伐克和奥地利第一共和国没有另收。"
)


def main():
    data = json.loads(OUT.read_text(encoding="utf-8"))
    features = [feat for feat in data["features"] if feat["properties"].get("source_id") != "swehist"]
    info = pyogrio.read_info(GPKG, layer="boundaries")
    transformer = Transformer.from_crs(info["crs"], "EPSG:4326", always_xy=True)
    _meta, table = pyogrio.read_arrow(
        GPKG, layer="boundaries", columns=["name", "start", "end"], where="type = 'County'",
    )
    names = table.column("name").to_pylist()
    starts = table.column("start").to_pylist()
    ends = table.column("end").to_pylist()
    geom_col = "wkb_geometry" if "wkb_geometry" in table.column_names else "geom"
    blobs = table.column(geom_col).to_pylist()
    missing = sorted({name for name in names if name not in ZH})
    if missing:
        raise SystemExit("缺译名 " + ", ".join(missing))
    url = "https://doi.org/10.5281/zenodo.23396621"
    for name, start, end, blob in zip(names, starts, ends, blobs):
        geom = clean_geom(transform(transformer.transform, wkb.loads(bytes(blob))), 0.03)
        if geom is None:
            continue
        start_s, end_s = f"{int(start):04d}-01-01", f"{int(end) + 1:04d}-01-01"
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"swehist-{len(features)}",
                "name_src": name,
                "name": ZH[name],
                "kind": "省",
                "nominal": "瑞典",
                "from": start_s,
                "until": end_s,
                "source_id": "swehist",
                "license": "CC BY 4.0",
                "url": url,
                "precision": NOTE,
            },
            "geometry": dump_geom(geom),
        })
    gaps = [item for item in data.get("gaps") or [] if "瑞典" not in item and "荷兰" not in item]
    gaps.append(
        "瑞典省用 swehist，约 1686 年至 1990 年。1991 年起待考。"
        "荷兰、比利时、挪威、丹麦、葡萄牙、匈牙利王国的州、捷克斯洛伐克、奥地利第一共和国没有可再分发的当年一级区划，待考。"
        "今天的省界没有拿来代替。"
    )
    data["features"] = features
    data["gaps"] = gaps
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("features", len(features))


if __name__ == "__main__":
    main()
