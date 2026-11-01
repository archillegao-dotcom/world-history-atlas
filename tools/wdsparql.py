"""
Wikidata SPARQL 小工具（构建脚本共用）。

默认使用 QLever 的 Wikidata 端点（https://qlever.dev/api/wikidata，弗赖堡大学，基于完整 Wikidata 转储，
通常每周更新），它对整库扫描类查询比官方 WDQS 快几十倍、且没有 60 秒超时；
可用环境变量 WHA_SPARQL_ENDPOINT=https://query.wikidata.org/sparql 切换回官方端点。
所有查询串行执行、带 User-Agent、失败退避重试，并把结果缓存到 data/cache/raw/。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WHA_DATA_DIR", ROOT / "data"))
RAW = DATA / "cache" / "raw"
ENDPOINT = os.environ.get("WHA_SPARQL_ENDPOINT", "https://qlever.dev/api/wikidata")
UA = ("WorldHistoryAtlas/0.2 (offline educational history atlas for students; "
      "borders from github.com/aourednik/historical-basemaps) python-requests")

PREFIXES = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX pqv: <http://www.wikidata.org/prop/qualifier/value/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""


def sparql(query: str, retries: int = 5) -> list[dict]:
    for attempt in range(retries):
        try:
            r = requests.post(ENDPOINT, data={"query": PREFIXES + query},
                              headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                              timeout=(20, 600))
            if r.status_code == 429 and "timed out" in r.text[:300]:
                # QLever 用 429 表示查询超时（默认约 30 秒）：重试没有意义，需要改写查询
                raise RuntimeError("query timed out on endpoint: " + r.text[:200])
            if r.status_code == 429 or r.status_code >= 500:
                wait = int(r.headers.get("Retry-After", 15 * (attempt + 1)))
                print(f"   HTTP {r.status_code}, waiting {wait}s", file=sys.stderr, flush=True)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
            return r.json()["results"]["bindings"]
        except RuntimeError:
            raise
        except (requests.RequestException, ValueError) as e:
            print(f"   error {e}, retry", file=sys.stderr, flush=True)
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("SPARQL failed after retries")


def cached(name: str, query: str) -> list[dict]:
    """按 名称+查询文本哈希 缓存；查询改了会自动重新抓取。设置 WHA_REFRESH=1 强制刷新。"""
    RAW.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(query.encode()).hexdigest()[:10]
    f = RAW / f"{name}_{h}.json.gz"
    if f.exists() and os.environ.get("WHA_REFRESH") != "1":
        return json.loads(gzip.decompress(f.read_bytes()))
    t = time.time()
    rows = sparql(query)
    f.write_bytes(gzip.compress(json.dumps(rows).encode()))
    print(f" -> {name}: {len(rows)} rows in {time.time() - t:.1f}s", flush=True)
    time.sleep(1)
    return rows


def v(b: dict, k: str):
    x = b.get(k)
    return x["value"] if x else None


def qid(uri: str | None):
    return uri.rsplit("/", 1)[-1] if uri else None


def parse_point(wkt: str | None):
    """'Point(lon lat)' -> [lon, lat]；带 <globe> 前缀（非地球坐标）的忽略。"""
    if not wkt or not wkt[:6].lower() == "point(":
        return None  # 空值，或带 <globe> 前缀的非地球坐标
    try:
        lon, lat = wkt[6:wkt.index(")")].split()
        return [round(float(lon), 4), round(float(lat), 4)]
    except ValueError:
        return None


def parse_time(val: str | None, prec: str | None):
    """RDF 时间（XSD 1.1 天文纪年：0000 = 公元前1年）-> {"y","m","d","p"}，y 为历史纪年（-1 = 公元前1年）。
    精度 p：6=千年 7=世纪 8=十年 9=年 10=月 11=日。"""
    if not val:
        return None
    neg = val.startswith("-")
    body = val[1:] if neg else val
    try:
        y, m, d = body[:body.index("T")].split("-")
        y, m, d = int(y), int(m), int(d)
    except ValueError:
        return None
    astro = -y if neg else y
    hy = astro - 1 if astro <= 0 else astro
    p = int(prec) if prec else 9
    return {"y": hy, "m": m if p >= 10 else 0, "d": d if p >= 11 else 0, "p": p}


def simplifier():
    """返回繁→简转换函数（OpenCC t2s）；未安装 opencc 时原样返回。"""
    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
        return cc.convert
    except ImportError:
        return lambda s: s


ZH_ORDER = ("zh-cn", "zh-hans", "zh", "zh-hant", "zh-tw", "zh-hk")


def pick_zh(d: dict[str, str]):
    for lang in ZH_ORDER:
        if d.get(lang):
            return d[lang], lang
    return None, None


def write_gz(path: Path, recs) -> None:
    path.write_bytes(gzip.compress(json.dumps(recs, ensure_ascii=False, separators=(",", ":")).encode()))
    print(f"wrote {path.name}: {len(recs)} records, {path.stat().st_size / 1e6:.2f} MB", flush=True)
