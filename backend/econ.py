"""
经济数据：Maddison Project Database 2023 与世界银行 WDI（data/econ.json.gz，由 tools/build_econ.py 生成）。

数据按**现代国家**（ISO3 代码）统计。历史时期的数值是「今天这个国家范围内」的估计（Maddison 的做法），
不是当时政权的数值；界面上始终这样注明。

取值规则（value_at）：
  - 有该年数据：直接用；
  - 没有：若前后两个数据点相隔不超过 max_gap 年，线性插值，并标注「插值（a 年与 b 年之间）」；
    Maddison 的 max_gap = 100（早期多为 1500/1600/1700/1820 等基准年），世界银行 = 5；
  - 所选年份晚于最后一个数据点不超过 carry 年（Maddison 5 年、世界银行 3 年）：用最后一个值，标注「最近数据」；
  - 其余一律「无数据」，不外推。
"""
from __future__ import annotations

import bisect
from pathlib import Path

from .datafile import read_json

# Maddison 中的已解体国家（整体数值）→ 今天的继承国
FORMER = {
    "SUN": ("前苏联整体", ["RUS", "UKR", "BLR", "KAZ", "UZB", "TKM", "KGZ", "TJK", "ARM", "AZE", "GEO", "MDA", "EST", "LVA", "LTU"]),
    "YUG": ("前南斯拉夫整体", ["SVN", "HRV", "BIH", "SRB", "MNE", "MKD", "XKX", "KOS"]),
    "CSK": ("捷克斯洛伐克整体", ["CZE", "SVK"]),
}
MEMBER_OF = {m: k for k, (_, ms) in FORMER.items() for m in ms}

MPD_CITE = ("Maddison Project Database 2023（Bolt, J. & van Zanden, J. L., 2024, “Maddison style estimates of the "
            "evolution of the world economy: A new 2023 update”, Journal of Economic Surveys），"
            "https://doi.org/10.34894/INZBF2")
MPD_URL = "https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023"

# 地图/面板可选指标
INDICATORS = {
    "mpd_gdppc": {"zh": "人均 GDP（Maddison，2011 年国际元）", "unit": "国际元", "src": "maddison", "key": "gdppc"},
    "mpd_gdp": {"zh": "GDP 总量（Maddison，2011 年国际元）", "unit": "国际元", "src": "maddison", "key": "gdp"},
    "mpd_pop": {"zh": "人口（Maddison）", "unit": "人", "src": "maddison", "key": "pop"},
}


def value_at(series: list | None, year: int, max_gap: int, carry: int) -> dict | None:
    if not series:
        return None
    ys = [p[0] for p in series]
    i = bisect.bisect_left(ys, year)
    if i < len(ys) and ys[i] == year:
        return {"v": series[i][1], "year": year}
    if 0 < i < len(ys):
        (a, va), (b, vb) = series[i - 1], series[i]
        if b - a <= max_gap:
            return {"v": va + (vb - va) * (year - a) / (b - a), "year": year, "interp": [a, b]}
        return None
    if i == len(ys) and year - ys[-1] <= carry:
        return {"v": series[-1][1], "year": ys[-1], "carried": True}
    return None


class EconStore:
    def __init__(self, data_dir: Path):
        d = read_json(Path(data_dir) / "econ.json.gz", {}) or {}
        self.mpd = d.get("maddison", {})
        self.wdi = d.get("wdi", {})
        self.wdi_meta = d.get("wdi_meta", {})
        self.ne_iso = d.get("ne_iso", {})
        self.overlap = d.get("overlap", {})
        self.built = d.get("built")
        # GDP 总量序列 = 人均 GDP × 人口（同一年都有时）
        for c in self.mpd.values():
            pop = dict(c["pop"])
            c["gdp"] = [[y, v * pop[y] * 1000] for y, v in c["gdppc"] if y in pop]
            c["pop_n"] = [[y, v * 1000] for y, v in c["pop"]]   # 千人 → 人
        self.indicators = dict(INDICATORS)
        for code, m in self.wdi_meta.items():
            self.indicators["wdi:" + code] = {"zh": m["zh"] + "（世界银行）", "unit": m["unit"], "src": "wdi", "key": code,
                                             "url": m["url"], "updated": m.get("updated")}

    def set_names(self, basemaps):
        """现代国家中文名：来自 Natural Earth 快照（2011）的 NAME_ZH。"""
        self.zh = {}
        try:
            for fid, f in basemaps.features(2011).items():
                iso = self.ne_iso.get(str(fid))
                if iso and f["props"].get("NAME_ZH"):
                    self.zh.setdefault(iso, f["props"]["NAME_ZH"])
        except Exception:  # noqa: BLE001
            pass

    def overlap_for(self, basemaps, snap) -> dict:
        """快照中每个多边形 → [[ISO3, 面积比例], ...]。过渡快照按多边形来源取对应快照的预计算结果；
        特殊地位领土（香港、澳门、格陵兰……）直接用 Natural Earth 中同一 Wikidata 条目的 ISO3。"""
        from .geo import norm_snap
        snap = norm_snap(snap)
        if snap == 2011:
            return {k: [[v, 1.0]] for k, v in self.ne_iso.items()}
        if not isinstance(snap, str):
            return self.overlap.get(str(snap), {})
        if not hasattr(self, "_qid_iso"):
            self._qid_iso = {}
            for fid, f in basemaps.features(2011).items():
                if f["props"].get("QID") and str(fid) in self.ne_iso:
                    self._qid_iso[f["props"]["QID"]] = self.ne_iso[str(fid)]
        out = {}
        for fid in basemaps.features(snap):
            s0, f0 = basemaps.origin(snap, fid)
            if s0 == "terr":
                if basemaps.trans.terr[f0].get("zone"):   # 实际控制区（如 1950 年的海南岛）：没有单独的经济数据
                    continue
                iso = self._qid_iso.get(basemaps.trans.terr[f0]["id"])
                if iso:
                    out[str(fid)] = [[iso, 1.0]]
            elif s0 == 2011:
                if str(f0) in self.ne_iso:
                    out[str(fid)] = [[self.ne_iso[str(f0)], 1.0]]
            else:
                ov = self.overlap.get(str(s0), {}).get(str(f0))
                if ov:
                    out[str(fid)] = ov
        return out

    def name(self, iso: str) -> str:
        return getattr(self, "zh", {}).get(iso) or (self.mpd.get(iso) or {}).get("name") or iso

    def series(self, ind: str, iso: str) -> list:
        m = self.indicators[ind]
        if m["src"] == "maddison":
            c = self.mpd.get(iso) or {}
            return c.get({"gdppc": "gdppc", "gdp": "gdp", "pop": "pop_n"}[m["key"]], [])
        return self.wdi.get(m["key"], {}).get(iso, [])

    def at(self, ind: str, iso: str, year: int) -> dict | None:
        m = self.indicators[ind]
        if m["src"] == "maddison":
            r = value_at(self.series(ind, iso), year, 100, 5)
            if r is None and iso in MEMBER_OF and m["key"] == "gdppc":
                # 继承国自己没有数据时，人均值可用解体前整体的数值（总量不能这样分摊）
                agg = MEMBER_OF[iso]
                r = value_at(self.series(ind, agg), year, 100, 5)
                if r:
                    r["agg"] = FORMER[agg][0]
            return r
        return value_at(self.series(ind, iso), year, 5, 3)

    def source_of(self, ind: str) -> dict:
        m = self.indicators[ind]
        if m["src"] == "maddison":
            return {"label": "Maddison Project Database 2023", "url": MPD_URL}
        return {"label": f"世界银行 WDI {m['key']}", "url": m["url"]}
