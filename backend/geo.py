"""
历史边界快照（historical-basemaps）的加载与空间查询。
- snapshot_for(date)：取「不晚于该日期的最近快照」；早于最早快照用最早的，晚于 2010 用 2010。
- polity(snapshot, fid)：返回 shapely 几何（已 prepare，可快速做点在面内判断）。
"""
from __future__ import annotations

import bisect
import gzip
import lzma
import json
from functools import lru_cache

from shapely import prepare
from shapely.geometry import shape

from . import config


class BasemapStore:
    def __init__(self) -> None:
        idx = json.loads((config.BASEMAP_DIR / "index.json").read_text(encoding="utf-8"))
        self.index = sorted(idx, key=lambda x: x["year"])
        self.years = [x["year"] for x in self.index]

    def snapshot_for(self, year: int) -> int:
        i = bisect.bisect_right(self.years, year) - 1
        return self.years[max(i, 0)]

    def next_snapshot(self, snap: int) -> int | None:
        i = self.years.index(snap)
        return self.years[i + 1] if i + 1 < len(self.years) else None

    @lru_cache(maxsize=64)
    def raw_bytes(self, snap: int) -> bytes:
        """返回 gzip 压缩的 GeoJSON 字节（直接以 Content-Encoding: gzip 发给浏览器）。
        打包版本中快照以 .geojson.xz 存放（更小），此时解压后重新用 gzip 压缩并缓存在内存里。"""
        gz = config.BASEMAP_DIR / f"{snap}.geojson.gz"
        if gz.exists():
            return gz.read_bytes()
        return gzip.compress(lzma.decompress((config.BASEMAP_DIR / f"{snap}.geojson.xz").read_bytes()), 6)

    @lru_cache(maxsize=8)
    def features(self, snap: int) -> dict[int, dict]:
        fc = json.loads(gzip.decompress(self.raw_bytes(snap)))
        out = {}
        for ft in fc["features"]:
            g = shape(ft["geometry"])
            prepare(g)
            out[ft["properties"]["fid"]] = {"props": ft["properties"], "geom": g}
        return out

    def polity(self, snap: int, fid: int) -> dict | None:
        return self.features(snap).get(fid)

    def locate(self, snap: int, lon: float, lat: float) -> dict | None:
        """点落在哪个政权多边形里（用于反查人物/事件所属政权）。"""
        from shapely.geometry import Point
        p = Point(lon, lat)
        for f in self.features(snap).values():
            if f["geom"].contains(p):
                return f
        return None
