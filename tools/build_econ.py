#!/usr/bin/env python3
"""
经济数据构建：
  1. Maddison Project Database 2023（Bolt & van Zanden 2024，格罗宁根大学 GGDC）官方文件 mpd2023_web.xlsx
     下载自 https://doi.org/10.34894/INZBF2（dataverse.nl 文件 421302）。取「Full data」表：
     countrycode, country, region, year, gdppc（2011 年国际元，PPP）, pop（千人）。
  2. 世界银行 WDI（API v2，https://api.worldbank.org/v2/）1960 年起的若干指标。
  3. 地图对应：Natural Earth 现代国家（2011 年快照的 fid）→ ISO3；每张历史快照的每个区域与现代国家的面积重叠比例。
输出 data/econ.json.gz：
  {"maddison": {ISO3: {"name","region","gdppc":[[年,值]...],"pop":[[年,值]...]}},
   "wdi": {指标代码: {ISO3: [[年,值]...]}}, "wdi_meta": {...},
   "ne_iso": {fid: ISO3}, "overlap": {快照: {fid: [[ISO3, 占该区域面积比例]...]}}, "built": 日期}
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import time
import urllib.request
from pathlib import Path

from shapely import STRtree
from shapely.geometry import shape
from shapely.validation import make_valid

from wdsparql import DATA, write_gz

RAW = DATA / "econ_raw"
MPD_URL = "https://dataverse.nl/api/access/datafile/421302"
UA = "WorldHistoryAtlas/0.4 (personal education app; contact: local user)"

# 世界银行指标（代码 → 中文名, 单位）
WDI = {
    "NY.GDP.MKTP.CD": ("GDP（现价美元）", "美元"),
    "NY.GDP.PCAP.CD": ("人均 GDP（现价美元）", "美元"),
    "NY.GDP.PCAP.PP.KD": ("人均 GDP（PPP，2021 年不变国际元）", "国际元"),
    "SP.POP.TOTL": ("人口", "人"),
    "SP.DYN.LE00.IN": ("预期寿命", "岁"),
    "NV.AGR.TOTL.ZS": ("农林渔业占 GDP", "%"),
    "NV.IND.TOTL.ZS": ("工业（含建筑）占 GDP", "%"),
    "NV.SRV.TOTL.ZS": ("服务业占 GDP", "%"),
    "SP.URB.TOTL.IN.ZS": ("城镇人口比例", "%"),
    "SE.ADT.LITR.ZS": ("成人识字率", "%"),
}


def get(url: str, ua: str = UA) -> bytes:
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            print("  retry", i, e, flush=True)
            time.sleep(3 * (i + 1))
    raise RuntimeError("download failed: " + url)


def maddison():
    import openpyxl
    f = RAW / "mpd2023_web.xlsx"
    if not f.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        # dataverse.nl 的反爬页面会拦截非浏览器 UA，这里用通用浏览器 UA 下载官方文件
        f.write_bytes(get(MPD_URL, ua="Mozilla/5.0 (WorldHistoryAtlas data build)"))
    ws = openpyxl.load_workbook(f, read_only=True)["Full data"]
    out = {}
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            assert r[:6] == ("countrycode", "country", "region", "year", "gdppc", "pop"), r
            continue
        code, name, region, year, gdppc, pop = r[:6]
        if not code or year is None:
            continue
        c = out.setdefault(code, {"name": name, "region": region, "gdppc": [], "pop": []})
        if gdppc is not None:
            c["gdppc"].append([int(year), round(float(gdppc), 1)])
        if pop is not None:
            c["pop"].append([int(year), round(float(pop), 3)])
    print("maddison countries:", len(out), "points:", sum(len(c["gdppc"]) + len(c["pop"]) for c in out.values()))
    return out


def wdi():
    data, meta = {}, {}
    for code, (zh, unit) in WDI.items():
        url = f"https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=20000&date=1960:{dt.date.today().year}"
        js = json.loads(get(url))
        if not isinstance(js, list) or len(js) < 2 or js[1] is None:
            print("  no data", code, js[:1])
            continue
        m, rows = js[0], js[1]
        d = {}
        name_en = None
        for x in rows:
            iso = x.get("countryiso3code")
            if not iso or x.get("value") is None:
                continue
            name_en = x["indicator"]["value"]
            d.setdefault(iso, []).append([int(x["date"]), x["value"]])
        for v in d.values():
            v.sort()
        data[code] = d
        meta[code] = {"zh": zh, "unit": unit, "en": name_en, "updated": m.get("lastupdated"),
                      "url": f"https://data.worldbank.org/indicator/{code}"}
        print("wdi", code, len(d), "countries", flush=True)
        time.sleep(1)
    return data, meta


def ne_mapping():
    raw = json.loads((DATA / "basemaps_raw" / "ne_50m_admin_0_countries.geojson").read_text(encoding="utf-8"))
    by_qid, by_name = {}, {}
    for f in raw["features"]:
        p = f["properties"]
        iso = p.get("ISO_A3") if p.get("ISO_A3") not in (None, "-99") else p.get("ISO_A3_EH")
        if iso in (None, "-99"):
            iso = p.get("ADM0_A3")
        if p.get("WIKIDATAID"):
            by_qid[p["WIKIDATAID"]] = iso
        by_name[p.get("NAME")] = iso
    fc = json.loads(gzip.decompress((DATA / "basemaps" / "2011.geojson.gz").read_bytes()))
    ne_iso, geoms, isos = {}, [], []
    for f in fc["features"]:
        p = f["properties"]
        iso = by_qid.get(p.get("QID")) or by_name.get(p.get("NAME"))
        if not iso:
            continue
        ne_iso[str(p["fid"])] = iso
        g = shape(f["geometry"])
        if not g.is_valid:
            g = make_valid(g)
        geoms.append(g)
        isos.append(iso)
    print("NE fids with ISO:", len(ne_iso))
    return ne_iso, geoms, isos


def overlaps(geoms, isos):
    tree = STRtree(geoms)
    idx = json.loads((DATA / "basemaps" / "index.json").read_text(encoding="utf-8"))
    out = {}
    for ent in idx:
        if ent["year"] == 2011:
            continue
        fc = json.loads(gzip.decompress((DATA / "basemaps" / ent["file"]).read_bytes()))
        m = {}
        for f in fc["features"]:
            g = shape(f["geometry"])
            if not g.is_valid:
                g = make_valid(g)
            if g.area == 0:
                continue
            parts = {}
            for j in tree.query(g, predicate="intersects"):
                try:
                    a = g.intersection(geoms[j]).area / g.area
                except Exception:  # noqa: BLE001  几何异常时跳过
                    continue
                if a >= 0.03:
                    parts[isos[j]] = parts.get(isos[j], 0) + a
            if parts:
                m[str(f["properties"]["fid"])] = [[k, round(v, 3)] for k, v in sorted(parts.items(), key=lambda x: -x[1])[:6]]
        out[str(ent["year"])] = m
        print("overlap", ent["year"], len(m), "/", len(fc["features"]), flush=True)
    return out


def main():
    mpd = maddison()
    w, meta = wdi()
    ne_iso, geoms, isos = ne_mapping()
    ov = overlaps(geoms, isos)
    write_gz(DATA / "econ.json.gz", {"maddison": mpd, "wdi": w, "wdi_meta": meta, "ne_iso": ne_iso, "overlap": ov,
                                     "built": dt.date.today().isoformat()})


if __name__ == "__main__":
    main()
