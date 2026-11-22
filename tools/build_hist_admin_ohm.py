"""从 OpenHistoricalMap 收下欧洲、中国以外、带起止日期的历史区划。

只写 CC0（关系上没有另外的 license 标签，或写明 CC0）。
没有 end_date 的不收：避免把还在用的现行边界当成当年的界。
几何接不上的不闭合、不补线，记入待考。
今天的 Natural Earth / geoBoundaries 不读。

用法：OHM_REBUILD=1 .venv/bin/python tools/build_hist_admin_ohm.py

直接运行会覆盖 data/curated/geom/hist_admin.geojson。
覆盖之后还要按代表点丢掉中国、欧洲和帝国全境，仓库里的文件已经滤过。
没有设置 OHM_REBUILD 时不下载、不覆盖。
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
OUT_GEOM = ROOT / "data" / "curated" / "geom" / "hist_admin.geojson"
OUT_META = ROOT / "data" / "curated" / "hist_admin.json"
UA = "world-history-atlas-research/1.0 (historical-admin; local)"
ENDPOINT = "https://overpass-api.openhistoricalmap.org/api/interpreter"
LICENSE = "CC0 1.0"
LICENSE_URL = "https://www.openhistoricalmap.org/copyright"
OK_LICENSE = {None, "", "CC0", "CC0 1.0", "cc0"}

CHINA_WORDS = (
    "吉林", "Kilin", "Jilin", "黑龙江", "Heilongjiang", "三江", "Sanjiang",
    "濱江", "滨江", "Binjiang", "奴兒干", "Nurgan", "满洲", "滿洲", "Manchukuo",
)


def overpass(query: str, timeout: int = 150) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def load_dump(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8")).get("elements") or []


def has_hangul(text: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def parse_start(raw: str) -> tuple[str, str] | None:
    s = raw.strip()
    if re.fullmatch(r"\d{3,4}", s):
        return f"{int(s):04d}-01-01", "起始只到年，日内待考。从该年1月1日起画，不是文书上的1月1日。"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s, ""
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return s + "-01", "起始只到月，日内待考。从该月1日起画，不是文书上的1日。"
    return None


def parse_end(raw: str) -> tuple[str, str] | None:
    """until 当天起不再画。只有年或月时，收到下一期的第一天，并写明不是文书日期。"""
    s = raw.strip()
    if re.fullmatch(r"\d{3,4}", s):
        return f"{int(s) + 1:04d}-01-01", "终止只到年，年内待考。收到次年1月1日，不是12月31日的文书。"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s, ""
    if re.fullmatch(r"\d{4}-\d{2}", s):
        year, month = int(s[:4]), int(s[5:7])
        if month == 12:
            nxt = f"{year + 1:04d}-01-01"
        else:
            nxt = f"{year:04d}-{month + 1:02d}-01"
        return nxt, "终止只到月，日内待考。收到次月1日，不是该月最后一天的文书。"
    return None


def classify(tags: dict, lon: float, lat: float, hinted: str | None) -> str:
    if hinted:
        if hinted == "ottoman" and lat > 34 and lon < 32:
            return "ottoman_europe_out"
        return hinted
    name = f"{tags.get('name') or ''} {tags.get('name:en') or ''}"
    bt = tags.get("border_type") or ""
    if any(w in name for w in CHINA_WORDS):
        return "china_out"
    if bt in {"vilayet", "eyalet"} or "Eyalet" in name or "Vilayet" in name:
        if lat > 34 and lon < 32:
            return "ottoman_europe_out"
        return "ottoman"
    if bt == "princely_state" or "Princely State" in name:
        return "british_india_princely"
    if "край" in name or "Krai" in name or "область" in name or "Oblast" in name:
        return "far_east_out"
    if has_hangul(name) or any(w in name for w in ("Gangwon", "Gyeongsang", "Hamgyong", "Hamkyong", "Ryanggang", "Kyŏngsang", "Kyongsang", "Pusan", "Busan")):
        return "korea"
    if any(w in name for w in ("Karafuto", "樺太", "Prefecture")) or name.endswith(("県", "縣", "府", "庁", "廳", "国", "國")):
        if lon > 122:
            return "japan"
    if 5 <= lat <= 10.5 and 79 <= lon <= 82.5:
        return "ceylon"
    if "Província" in name or "Provincia" in name:
        return "portuguese_india"
    if any(w in name for w in ("Gilgit", "Azad", "Baltistan")):
        return "south_asia_other"
    if bt == "province" and 5 <= lat <= 38 and 60 <= lon <= 99:
        return "british_india"
    return "review"


def key_pt(pt):
    return (round(pt[0], 5), round(pt[1], 5))


def stitch(chunks: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    unused = []
    for chunk in chunks:
        pts = [key_pt(p) for p in chunk]
        cleaned = [pts[0]]
        for p in pts[1:]:
            if p != cleaned[-1]:
                cleaned.append(p)
        if len(cleaned) >= 2:
            unused.append(cleaned)
    rings = []
    while unused:
        ring = unused.pop(0)
        progressed = True
        while progressed and ring[0] != ring[-1]:
            progressed = False
            for i, other in enumerate(unused):
                if ring[-1] == other[0]:
                    ring.extend(other[1:])
                elif ring[-1] == other[-1]:
                    ring.extend(reversed(other[:-1]))
                elif ring[0] == other[-1]:
                    ring = other[:-1] + ring
                elif ring[0] == other[0]:
                    ring = list(reversed(other[1:])) + ring
                else:
                    continue
                unused.pop(i)
                progressed = True
                break
        if ring[0] != ring[-1]:
            continue
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def relation_shape(element: dict):
    outers, inners = [], []
    for member in element.get("members") or []:
        if member.get("type") != "way":
            continue
        geom = member.get("geometry") or []
        if len(geom) < 2:
            continue
        line = [(p["lon"], p["lat"]) for p in geom]
        role = member.get("role") or "outer"
        if role == "inner":
            inners.append(line)
        else:
            outers.append(line)
    outer_rings = stitch(outers)
    inner_rings = stitch(inners)
    if not outer_rings:
        return None
    holes = []
    for ring in inner_rings:
        try:
            holes.append(Polygon(ring))
        except Exception:
            continue
    polygons = []
    for ring in outer_rings:
        try:
            poly = Polygon(ring)
        except Exception:
            continue
        if not poly.is_valid:
            poly = make_valid(poly)
        if holes:
            inside = [h for h in holes if poly.contains(h.representative_point())]
            if inside:
                poly = poly.difference(MultiPolygon(inside) if len(inside) > 1 else inside[0])
        if poly.is_empty:
            continue
        if poly.geom_type == "Polygon":
            polygons.append(poly)
        elif poly.geom_type == "MultiPolygon":
            polygons.extend(list(poly.geoms))
        elif poly.geom_type == "GeometryCollection":
            polygons.extend([g for g in poly.geoms if g.geom_type == "Polygon"])
    if not polygons:
        return None
    geom = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
    geom = make_valid(geom)
    if geom.is_empty:
        return None
    tol = 0.05 if geom.area > 30 else 0.02
    geom = geom.simplify(tol, preserve_topology=True)
    if geom.is_empty or geom.area <= 0:
        return None
    return geom


def round_geom(obj):
    if isinstance(obj, float):
        return round(obj, 3)
    if isinstance(obj, list):
        return [round_geom(x) for x in obj]
    if isinstance(obj, dict):
        return {k: round_geom(v) for k, v in obj.items()}
    return obj


def fetch_geom(ids: list[int]) -> list[dict]:
    got = []
    for i in range(0, len(ids), 20):
        batch = ids[i:i + 20]
        idlist = ",".join(str(n) for n in batch)
        query = f"[out:json][timeout:120];relation(id:{idlist});out geom;"
        print(f"geom {i + 1}-{i + len(batch)} / {len(ids)}", flush=True)
        data = overpass(query, timeout=180)
        got.extend(data.get("elements") or [])
    return got


def main() -> None:
    if os.environ.get("OHM_REBUILD") != "1":
        print("跳过。要重新下载请设 OHM_REBUILD=1。不覆盖现有几何。")
        return
    hinted: dict[int, str] = {}
    elements: dict[int, dict] = {}
    for path, hint in (
        ("/tmp/ohm_india_prov.json", None),
        ("/tmp/ohm_india_pr.json", None),
        ("/tmp/ohm_ottoman.json", None),
        ("/tmp/ohm_japan.json", None),
    ):
        for el in load_dump(path):
            elements[el["id"]] = el
            if hint:
                hinted[el["id"]] = hint

    extra = {
        "taiwan": '[out:json][timeout:40];relation(21.8,119.9,25.4,122.05)["boundary"="administrative"]["start_date"]["end_date"];out tags;',
        "indochina": '[out:json][timeout:50];relation(8.2,102.0,23.5,109.6)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "dei": '[out:json][timeout:50];relation(-8.5,105.0,-5.8,114.8)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "us": '[out:json][timeout:70];relation(24,-125,49,-66)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "mexico": '[out:json][timeout:40];relation(14,-118,32.8,-86)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "brazil": '[out:json][timeout:50];relation(-34,-74,6,-34)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "argentina": '[out:json][timeout:40];relation(-55,-73,-21,-53)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "central_asia": '[out:json][timeout:40];relation(35,50,49,80)["boundary"="administrative"]["admin_level"="4"]["start_date"]["end_date"];out tags;',
        "africa": '[out:json][timeout:50];relation(-35,-18,37,52)["boundary"="administrative"]["admin_level"="3"]["start_date"]["end_date"];out tags;',
        "indochina_name": '[out:json][timeout:30];relation["name:en"~"Cochinchina|Annam|Tonkin"]["boundary"="administrative"];out tags;',
    }
    extra_counts = {}
    for region, query in extra.items():
        try:
            data = overpass(query, timeout=100)
        except Exception as exc:  # noqa: BLE001
            print("query fail", region, exc, flush=True)
            extra_counts[region] = f"查询失败：{exc.__class__.__name__}"
            continue
        els = data.get("elements") or []
        extra_counts[region] = len(els)
        print(region, len(els), flush=True)
        for el in els[:8]:
            t = el.get("tags") or {}
            print(" ", el["id"], t.get("name") or t.get("name:en"), t.get("start_date"), t.get("end_date"), t.get("admin_level"))
        if len(els) > 80:
            print("skip bulk", region, len(els), flush=True)
            extra_counts[region] = f"{len(els)} 条，超过 80，未逐条核验，不整批画入"
            continue
        for el in els:
            elements[el["id"]] = el
            hinted[el["id"]] = "indochina" if region == "indochina_name" else region

    candidates = []
    rejected = []
    for el in elements.values():
        tags = el.get("tags") or {}
        if tags.get("license") not in OK_LICENSE:
            rejected.append({"ohm": el["id"], "name": tags.get("name"), "why": f"许可证不是 CC0：{tags.get('license')}"})
            continue
        if not tags.get("start_date") or not tags.get("end_date"):
            continue
        start = parse_start(str(tags["start_date"]))
        end = parse_end(str(tags["end_date"]))
        if not start or not end:
            rejected.append({"ohm": el["id"], "name": tags.get("name"), "why": "日期无法解析", "start": tags.get("start_date"), "end": tags.get("end_date")})
            continue
        if not (start[0] < end[0]):
            rejected.append({"ohm": el["id"], "name": tags.get("name"), "why": "起止颠倒或同日，不画", "start": tags.get("start_date"), "end": tags.get("end_date")})
            continue
        candidates.append((el["id"], tags, start, end))

    print("candidates", len(candidates), flush=True)
    geoms = {el["id"]: el for el in fetch_geom([c[0] for c in candidates])}
    features = []
    by_region = Counter()
    for oid, tags, start, end in candidates:
        el = geoms.get(oid)
        if not el:
            rejected.append({"ohm": oid, "name": tags.get("name"), "why": "没有返回几何"})
            continue
        geom = relation_shape(el)
        if geom is None:
            rejected.append({"ohm": oid, "name": tags.get("name"), "why": "线没有接成闭合边界，不补、不画"})
            continue
        pt = geom.representative_point()
        region = classify(tags, pt.x, pt.y, hinted.get(oid))
        if region.endswith("_out") or region == "review":
            rejected.append({
                "ohm": oid, "name": tags.get("name") or tags.get("name:en"),
                "why": "欧洲、中国、远东或无法归区，本层不画", "region": region,
            })
            continue
        note = " ".join(p for p in (start[1], end[1]) if p)
        props = {
            "id": f"ohm-{oid}",
            "ohm_id": oid,
            "name": tags.get("name") or tags.get("name:en") or "",
            "name_en": tags.get("name:en"),
            "name_zh": tags.get("name:zh"),
            "region": region,
            "kind": tags.get("border_type") or "行政区",
            "from": start[0],
            "until": end[0],
            "raw_start": str(tags.get("start_date")),
            "raw_end": str(tags.get("end_date")),
            "date_note": note,
            "license": LICENSE,
            "license_url": LICENSE_URL,
            "source": "OpenHistoricalMap",
            "source_url": f"https://www.openhistoricalmap.org/relation/{oid}",
            "precision": "OpenHistoricalMap 关系几何，简化到约 0.02–0.05 度。未在本地对照原图重测。不是今天的行政区。",
        }
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": round_geom(mapping(geom)),
        })
        by_region[region] += 1

    OUT_GEOM.parent.mkdir(parents=True, exist_ok=True)
    OUT_GEOM.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": features,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meta = {
        "retrieved": "2026-11-22",
        "source": "OpenHistoricalMap",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "endpoint": ENDPOINT,
        "rule": "只收同时有 start_date 和 end_date、许可证为 CC0、并且能接成闭合边界的关系。没有结束日期的现行边界不收。欧洲各国省界和中国不收。几何接不上就不画。",
        "counts": dict(by_region),
        "extra_query_counts": extra_counts,
        "rejected_sample": rejected[:80],
        "rejected_total": len(rejected),
        "feature_total": len(features),
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("features", len(features), dict(by_region), flush=True)
    print("rejected", len(rejected), flush=True)
    print("wrote", OUT_GEOM, OUT_GEOM.stat().st_size, flush=True)


if __name__ == "__main__":
    main()
