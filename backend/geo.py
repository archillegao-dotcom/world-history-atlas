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

from .geolock import locked_lru

from shapely import make_valid, prepare
from shapely.geometry import shape

from . import config


def norm_snap(snap):
    """快照 ID：真实快照为 int（年份），过渡快照为 "基础年份@YYYYMMDD" 字符串，CShapes 快照为 "cs@YYYYMMDD"。"""
    if isinstance(snap, str) and "@" not in snap:
        return int(snap)
    return snap


class BasemapStore:
    def __init__(self) -> None:
        idx = json.loads((config.BASEMAP_DIR / "index.json").read_text(encoding="utf-8"))
        self.index = sorted(idx, key=lambda x: x["year"])
        self.years = [x["year"] for x in self.index]
        from .transitions import Transitions
        self.trans = Transitions(self, config.DATA_DIR)
        from .cshapes import CShapes
        self.cs = CShapes(self, config.DATA_DIR)

    # ---------------------------------------------------------------- 过渡快照（见 transitions.py）
    def snapshot_at(self, date):
        """所选日期使用的快照 ID：1886–2019 用 CShapes（cs@…）；其余为基础快照 + 已生效的过渡修正。"""
        if self.cs.covers(date):
            return self.cs.vid(date)
        return self.trans.vid(self.snapshot_for(date.y), date)

    @staticmethod
    def is_cs(snap) -> bool:
        return isinstance(snap, str) and snap.startswith("cs@")

    def base_of(self, snap) -> int:
        snap = norm_snap(snap)
        if self.is_cs(snap):
            return self.base_of(self.cs.hb_vid(self.cs.parse(snap)))
        return int(snap.split("@")[0]) if isinstance(snap, str) else snap

    def valid(self, snap) -> bool:
        snap = norm_snap(snap)
        if self.is_cs(snap):
            try:
                return self.cs.ok and bool(self.cs.parse(snap))
            except ValueError:
                return False
        if isinstance(snap, str):
            try:
                return int(snap.split("@")[0]) in self.years and bool(self.trans.parse(snap))
            except ValueError:
                return False
        return snap in self.years

    def origin(self, snap, fid):
        """过渡快照中的多边形 → (来源快照, 来源 fid)；特殊领土返回 ("terr", 序号)。真实快照原样返回。"""
        snap = norm_snap(snap)
        if self.is_cs(snap):
            return self.cs.compose(snap)[1].get(fid, (snap, fid))
        if isinstance(snap, str):
            return self.trans.compose(snap)[1].get(fid, (self.base_of(snap), fid))
        return snap, fid

    def notes(self, snap):
        snap = norm_snap(snap)
        if self.is_cs(snap):
            return self.cs.compose(snap)[2]
        return self.trans.compose(snap)[2] if isinstance(snap, str) else []

    def snapshot_for(self, year: int) -> int:
        i = bisect.bisect_right(self.years, year) - 1
        return self.years[max(i, 0)]

    def next_snapshot(self, snap: int) -> int | None:
        i = self.years.index(snap)
        return self.years[i + 1] if i + 1 < len(self.years) else None

    @lru_cache(maxsize=64)
    def raw_bytes(self, snap) -> bytes:
        """返回 gzip 压缩的 GeoJSON 字节（直接以 Content-Encoding: gzip 发给浏览器）。
        打包版本中快照以 .geojson.xz 存放（更小），此时解压后重新用 gzip 压缩并缓存在内存里。"""
        snap = norm_snap(snap)
        if isinstance(snap, str):
            from shapely.geometry import mapping
            feats = self.cs.compose(snap)[0] if self.is_cs(snap) else self.trans.compose(snap)[0]
            # v0.6.1：求差/求交后可能剩下线、点或 GeometryCollection；只发多边形部分，
            # 否则前端把点画成 Marker（没有 setStyle/bringToBack），整个底图图层出错、点击无反应（如 1410、685、1575 年）
            from shapely.geometry import MultiPolygon, Polygon
            def poly_only(g):
                if g is None or g.is_empty:
                    return None
                if isinstance(g, (Polygon, MultiPolygon)):
                    return g
                parts = [p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
                ps = [q for p in parts for q in (p.geoms if isinstance(p, MultiPolygon) else [p])]
                return MultiPolygon(ps) if ps else None
            out = []
            for f in feats.values():
                g = poly_only(f["geom"])
                if g is not None:
                    out.append({"type": "Feature", "properties": f["props"], "geometry": mapping(g)})
            fc = {"type": "FeatureCollection", "features": out}
            return gzip.compress(json.dumps(fc, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
        gz = config.BASEMAP_DIR / f"{snap}.geojson.gz"
        if gz.exists():
            return gz.read_bytes()
        return gzip.compress(lzma.decompress((config.BASEMAP_DIR / f"{snap}.geojson.xz").read_bytes()), 6)

    def features(self, snap) -> dict[int, dict]:
        snap = norm_snap(snap)
        if self.is_cs(snap):
            return self.cs.compose(snap)[0]
        if isinstance(snap, str):
            return self.trans.compose(snap)[0]
        return self._features(snap)

    @locked_lru(maxsize=12)
    def _features(self, snap: int) -> dict[int, dict]:
        fc = json.loads(gzip.decompress(self.raw_bytes(snap)))
        out = {}
        for ft in fc["features"]:
            g = shape(ft["geometry"])
            if not g.is_valid:   # 少数快照多边形自相交：修复后再做空间运算（过渡层需要求交/求差）
                g = make_valid(g)
            prepare(g)
            out[ft["properties"]["fid"]] = {"props": ft["properties"], "geom": g}
        return out

    def polity(self, snap, fid: int) -> dict | None:
        return self.features(snap).get(fid)

    def locate(self, snap, lon: float, lat: float) -> dict | None:
        """点落在哪个政权多边形里（用于反查人物/事件所属政权）。"""
        from shapely.geometry import Point
        p = Point(lon, lat)
        feats = self.features(snap).values()
        for f in feats:
            if f["geom"].contains(p):
                return f
        # 海岸/小岛附近的点（底图海岸线较粗，如 1:50m 的香港、努克）：取 0.15° 以内最近的多边形
        best, bd = None, 0.15
        for f in feats:
            d = f["geom"].distance(p)
            if d < bd:
                best, bd = f, d
        return best
