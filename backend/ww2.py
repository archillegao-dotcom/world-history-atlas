"""
二战（及其他按日期的战线）叠加：在 CShapes 合成结果上
  1) 1938-02 – 1945-05 欧洲：Stanford「Building the New Order」按月边界（吞并/新设实体、占领状态），替换该范围内的 CShapes 法理边界；
  2) 战线（data/curated/war_fronts_hist.json）：按节点阶梯（每个节点注明适用起止日期），用折线把战区切成两侧，
     交战一方的领土落在对方一侧的部分单独成为「占领区/解放区」多边形（可点击，带来源与精度说明）。
"""
from __future__ import annotations

import bisect
import json
from functools import lru_cache

from shapely import make_valid, prepare
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import split, unary_union

from .datafile import read_json

OFF_STAN, OFF_FRONT = 370000, 380000


def _poly(pts):
    return make_valid(Polygon(pts))


class WarLayers:
    def __init__(self, data_dir):
        self.stan = read_json(data_dir / "ww2_europe.json.gz", {}) or {}
        self.mdates = [m["date"] for m in self.stan.get("months", [])]
        p = data_dir / "curated" / "war_fronts_hist.json"
        self.cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        self.snames = self.cur.get("stanford_names", {})
        self.theatres = self.cur.get("theatres", [])
        self._g = {}

    # ---------- Stanford 按月边界 ----------
    def stan_month(self, k8: int):
        """所选日期使用的月末快照：日期之前（不含当天）最近的一个月末；1938-03-01 前、1945-06-01 起不用。"""
        if not self.mdates or k8 < 19380301 or k8 >= 19450601:
            return None
        # 提前使用下一张月末快照的时段（如 1939-09-28《德苏边界友好条约》划定的瓜分线，Stanford 要到 10 月末快照才画出）
        for a, b, m in self.cur.get("stanford_month_override", []):
            if a <= k8 < b:
                return m
        i = bisect.bisect_left(self.mdates, k8) - 1
        return self.mdates[i] if i >= 0 else None

    def stan_geom(self, gid):
        if gid not in self._g:
            self._g[gid] = make_valid(shape(self.stan["geoms"][gid]))
        return self._g[gid]

    def stan_feats(self, mdate):
        m = self.stan["months"][self.mdates.index(mdate)]
        return [(k, f) for k, f in enumerate(m["feats"])]

    def marks(self):
        out = set()
        for a, b, m in self.cur.get("stanford_month_override", []):
            out.add(a)
        for m in self.mdates:
            y, mo = m // 10000, (m // 100) % 100
            nxt = (y + (mo == 12)) * 10000 + (1 if mo == 12 else mo + 1) * 100 + 1
            out.add(nxt)
        for t in self.theatres:
            for s in t["steps"]:
                for k in ("from", "until"):
                    if s.get(k):
                        out.add(int(s[k].replace("-", "")))
                for p in s.get("allied_pockets", []) + s.get("axis_pockets", []):
                    for k in ("from", "until"):
                        if p.get(k):
                            out.add(int(p[k].replace("-", "")))
        return out

    def stan_cands(self, name, status, k8):
        """Stanford 要素 → 候选 [qid, method, score, from, to] 或 ("gw", gwcode)。"""
        r = self.snames.get(name)
        if not r:
            return []
        if "gw" in r:
            return [("gw", r["gw"])]
        out = []
        for a, b, q in r.get("periods", []):
            out.append([q, "ww2", 600, int(a.replace("-", "")) if a else None, int(b.replace("-", "")) if b else None])
        if r.get("qid"):
            out.append([r["qid"], "ww2", 590, None, None])
        return out

    def side(self, name, status, k8):
        """要素在该日期属于哪一方：axis / allied / neutral（Stanford 的 Foreign_Po + 人工整理的阵营变更日期）。"""
        r = self.snames.get(name, {})
        for a, b, sd in r.get("sides", []):
            if (a is None or int(a.replace("-", "")) <= k8) and (b is None or k8 < int(b.replace("-", ""))):
                return sd
        s = (status or "").lower()
        if "neutral" in s:
            return "neutral"
        if "allie" in s or "war with" in s or "belligerent" in s:
            return "allied"
        if s:
            return "axis"
        return r.get("side", "neutral")

    # ---------- 战线 ----------
    @lru_cache(maxsize=512)
    def theatre_area(self, ti, si, k8):
        """第 ti 个战区第 si 个节点：轴心一侧的多边形（含轴心孤立据点，减去盟军孤立据点）。"""
        t = self.theatres[ti]
        s = t["steps"][si]
        bb = box(*t["bbox"])
        if s.get("line"):
            pts = [tuple(p) for p in s["line"]]
            x0, y0, x1, y1 = t["bbox"]
            if t.get("orient", "ns") == "ns":
                pts = [(pts[0][0], y1 + 1)] + pts + [(pts[-1][0], y0 - 1)]
            else:
                pts = [(x0 - 1, pts[0][1])] + pts + [(x1 + 1, pts[-1][1])]
            parts = list(split(bb, LineString(pts)).geoms)
            ap = shape({"type": "Point", "coordinates": s.get("axis_point") or t["axis_point"]})
            area = next((p for p in parts if p.contains(ap)), None)
            if area is None:
                area = Polygon()
        else:
            area = Polygon()
            if s.get("axis_default", True) and not s.get("axis_pockets") and not s.get("allied_pockets"):
                area = Polygon()
            if s.get("rest_axis"):
                area = bb
        def act(p):
            return (not p.get("from") or int(p["from"].replace("-", "")) <= k8) and (not p.get("until") or k8 < int(p["until"].replace("-", "")))
        ax = [_poly(p["polygon"]) for p in s.get("axis_pockets", []) if act(p)]
        al = [_poly(p["polygon"]) for p in s.get("allied_pockets", []) if act(p)]
        if ax:
            area = unary_union([area] + ax)
        if al:
            area = area.difference(unary_union(al))
        return make_valid(area)

    def active_steps(self, k8):
        out = []
        for ti, t in enumerate(self.theatres):
            for si, s in enumerate(t["steps"]):
                a = int(s["from"].replace("-", ""))
                b = int(s["until"].replace("-", ""))
                if a <= k8 < b:
                    out.append((ti, si))
                    break
        return out

    STATUS_ZH = {"Neutral": "中立", "Axis": "轴心国", "Allies": "同盟国", "Allied": "同盟国", "Axis-aligned": "与轴心国结盟",
                 "German-occupied": "德国占领", "Italian-occupied": "意大利占领", "German Protectorate": "德国保护国", "Italian Protectorate": "意大利保护国",
                 "Romanian-occupied": "罗马尼亚占领", "Belligerent": "交战国", "War with Soviet Union": "与苏联交战", "German,Soviet-occupied": "德国、苏联占领",
                 "German, Italian-occupied": "德国、意大利占领", "German, Bulgarian-occupied": "德国、保加利亚占领",
                 "German, Italian, Bulgarian-occupied": "德国、意大利、保加利亚占领", "Axis, German, Italian-occupied": "轴心国（德、意占领）",
                 "Axis and German-occupied": "轴心国（德国占领）", "Axis and German, Italian-occupied": "轴心国（德、意占领）"}

    def status_zh(self, st):
        return self.STATUS_ZH.get(st or "", st or None)

    def side_gw(self, t, gw, name, k8):
        for r in t.get("sides", []):
            if (gw is not None and gw in r.get("gw", [])) or name in r.get("names", []):
                for a, b, sd in r["periods"]:
                    if (a is None or int(a.replace("-", "")) <= k8) and (b is None or k8 < int(b.replace("-", ""))):
                        return sd
        return None

    @staticmethod
    def polys(g):
        from shapely.geometry import MultiPolygon
        if g is None or g.is_empty:
            return None
        if g.geom_type == "GeometryCollection":
            ps = [q for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon") for q in getattr(p, "geoms", [p])]
            g = MultiPolygon(ps) if ps else None
        if g is None or g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            return None
        return g

    def label(self, t, held, name, piece, k8):
        pt = piece.representative_point()
        for r in t.get("labels", []):
            if r["held"] != held:
                continue
            if r.get("names") and name not in r["names"]:
                continue
            if r.get("not_names") and name in r["not_names"]:
                continue
            if r.get("from") and k8 < int(r["from"].replace("-", "")):
                continue
            if r.get("until") and k8 >= int(r["until"].replace("-", "")):
                continue
            if r.get("within") and not _poly(r["within"]).contains(pt):
                continue
            return r
        return None
