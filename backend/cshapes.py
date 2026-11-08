"""
CShapes 2.0 底图（1886-01-01 至 2019-12-31）：按日期精确的国家/殖民地边界（Schvitz et al. 2022，ETH Zürich，CC BY-NC-SA 4.0）。

快照 ID 形如 "cs@19920101"：所选日期之前最近一次边界/地位变化的日期（同一 ID ⇒ 地图完全相同）。合成内容：
  300000 + i  CShapes 第 i 行（国家、殖民地、保护国、托管地；带 gwcode、地位、宗主国）
  390000 + j  补充的微型国家/小岛国（Natural Earth 1:10m，CShapes 未单列的梵蒂冈、摩纳哥、圣马力诺……）及满洲国（近似）
  200000 + i  特殊地位领土（香港、澳门、格陵兰……，与过渡层相同）
  其余        CShapes 没有覆盖的地区（如 1932 年前的阿拉伯半岛内陆）仍用 historical-basemaps 的过渡快照，按 CShapes 范围裁剪
"""
from __future__ import annotations

import bisect
from functools import lru_cache

from .geolock import locked_lru

from shapely import STRtree, make_valid, prepare
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from .datafile import read_json
from .timeutil import HDate
from .transitions import tkey
from .ww2 import OFF_STAN

OFF_ROW, OFF_EXTRA, OFF_TERR = 300000, 390000, 200000
LO, HI = 18860101, 20200101
STATUS_ZH = {"colony": "殖民地", "protectorate": "保护国", "mandate": "托管地", "occupied": "占领区", "independent": "独立国家", "N/A": "地位不明",
             "roc_province": "中华民国省份（台湾光复后，中央政府尚未迁台）"}


def _local_diff(g, tree, geoms):
    """g 减去 geoms 中与之相交的部分（只对局部候选做 union，避免对全球覆盖做布尔运算）。"""
    idx = tree.query(g, predicate="intersects")
    if len(idx) == 0:
        return g
    loc = unary_union([geoms[i] for i in idx])
    if loc.contains(g):
        return None
    try:
        r = make_valid(g.difference(loc))
    except Exception:
        r = make_valid(g.buffer(0).difference(loc.buffer(0)))
    return None if r.is_empty else r


def ymd_of(d: HDate) -> int:
    return d.y * 10000 + (d.m or 1) * 100 + (d.d or 1)


def _apply_colony_fixes(rows, gw):
    """签约日、生效日、实控日不一致时，不沿用 CShapes 把整块多边形从签约日标成后来的国家。

    台湾 gw 713：CShapes 殖民地行自 1895-04-17（《马关条约》签署）起，分期原先整段标成日治，
    名称匹配又会把英文名 Taiwan 的中华民国 Q865 排到日治政权前面。
    - 1895-04-17 签署，1895-05-08 在烟台换文生效。此前不是日本实控。
    - 1895-05-23 台湾民主国宣布成立，1895-10-21 台南开城后结束。全岛一块多边形不能表示日军自北向南的推进。
    - 1895-05-08 至 05-23 没有稳定的新政权，仍标清治时期并在 sources 里说明，不标日本、不标中华民国。
    - 日治自 1895-10-21 起。中文维基「乙未战争」把战事记到 1895-11-18，此处不把 10-21 写成一切抵抗结束。
    - 1945-10-25 台北受降（台湾光复）之后才是中华民国。1945-08-15 至 10-24 日本总督府仍在管治，不把投降公告日写成已经移交。
    - CShapes 殖民地行止于 1945-08-15、独立行起于 1949-12-08（国民政府迁台）。中间若没有多边形，点击会落到别的底图上。
      这里把殖民地行延长到 1945-10-25，并复用同一条岛屿多边形补上 1945-10-25 至 1949-12-08，不新画海岸线。
      澎湖不在这条多边形内（约东经 120.05° 以西），不另造。
    https://en.wikipedia.org/wiki/Treaty_of_Shimonoseki
    https://en.wikipedia.org/wiki/Republic_of_Formosa
    https://en.wikipedia.org/wiki/Capitulation_of_Tainan
    https://zh.wikipedia.org/wiki/乙未戰爭
    https://en.wikipedia.org/wiki/Retrocession_Day

    朝鲜 gw 730：CShapes 把殖民地行写成 1910-08-23（签署次日）。条约 1910-08-22 签署、1910-08-29 公布生效。
    https://en.wikipedia.org/wiki/Japan%E2%80%93Korea_Treaty_of_1910

    南桦太 gw 7351：CShapes 行自 1905-09-05（《朴茨茅斯条约》签署）起，但没有分期，只会落到宗主国弱候选。
    补成大日本帝国。日军 1905 年 7 月已登陆，多边形本身从签约日才有，不另造 7 月的边界。
    https://en.wikipedia.org/wiki/Treaty_of_Portsmouth
    https://en.wikipedia.org/wiki/Karafuto_Prefecture
    """
    for r in rows:
        if r.get("gw") == 730 and r.get("status") == "independent" and r.get("to") == 19100823:
            r["to"] = 19100829
        if r.get("gw") == 730 and r.get("status") == "colony" and r.get("from") == 19100823:
            r["from"] = 19100829
    fixes = {
        713: [[18950417, 18950523, "Q391189"], [18950523, 18951021, "Q319881"],
              [18951021, 19451025, "Q137816"], [19451025, None, "Q865"]],
        7351: [[19050905, 19450815, "Q188712"]],
    }
    for code, periods in fixes.items():
        gi = gw.setdefault(code, {"names": [], "periods": [], "ne": None})
        gi["periods"] = periods
    # 台湾岛多边形空档：复用 CShapes 已有的同一块岛屿几何。两条原始行面积相同（约 3.19），范围都是东经 120.05–122.0、北纬 21.93–25.28。
    col = next((r for r in rows if r.get("gw") == 713 and r.get("status") == "colony" and r.get("to") == 19450815), None)
    ind = next((r for r in rows if r.get("gw") == 713 and r.get("status") == "independent" and r.get("from") == 19491208), None)
    if col is not None:
        col["to"] = 19451025
    if ind is not None and not any(r.get("gw") == 713 and r.get("from") == 19451025 and r.get("to") == 19491208 for r in rows):
        gap = dict(ind)
        gap["geom"] = ind["geom"]
        gap["i"] = len(rows)
        gap["from"] = 19451025
        gap["to"] = 19491208
        gap["status"] = "roc_province"
        rows.append(gap)
    # CShapes 在 1945-08-15 把台湾岛并回中国多边形（gw 710），点选会先命中中国、标成中华民国。
    # 从这些中国行里挖掉已有的台湾岛几何，让上面的分期行露出来。不新画海岸线。
    if ind is not None:
        tw = make_valid(shape(ind["geom"]))
        for r in list(rows):
            if r.get("gw") != 710:
                continue
            a, b = r.get("from") or 0, r.get("to")
            if b is not None and b <= 19450815:
                continue
            if a >= 19491208 or a < 19450815:
                continue
            g = make_valid(shape(r["geom"]))
            if not g.intersects(tw):
                continue
            ng = make_valid(g.difference(tw))
            if not ng.is_empty:
                r["geom"] = mapping(ng)


class CShapes:
    def __init__(self, store, data_dir):
        self.store = store
        self._cut_cache, self._simp_cache, self._hb_cache = {}, {}, {}
        d = read_json(data_dir / "cshapes.json.gz", {}) or {}
        self.ok = bool(d.get("rows"))
        self.rows = d.get("rows", [])
        self.extras = d.get("extras", [])
        self.gw = {int(k): v for k, v in (d.get("gw") or {}).items()}
        _apply_colony_fixes(self.rows, self.gw)
        self.source = d.get("source")
        marks = {LO}
        for r in self.rows + self.extras:
            for k in ("from", "to"):
                if r.get(k):
                    marks.add(r[k])
        for t in store.trans.terr:
            for k in ("from", "to"):
                if t.get(k) and t[k].get("y"):
                    marks.add(t[k]["y"] * 10000 + (t[k].get("m") or 1) * 100 + (t[k].get("d") or 1))
        from .ww2 import WarLayers
        self.war = WarLayers(data_dir)
        marks |= self.war.marks()
        self.marks = sorted(m for m in marks if LO <= m < HI)
        self._g = {}

    def covers(self, date: HDate) -> bool:
        return self.ok and date.y >= 1886 and LO <= ymd_of(date) < HI

    def hb_vid(self, date: HDate):
        return self.store.trans.vid(self.store.snapshot_for(date.y), date)

    def vid(self, date: HDate) -> str:
        k = ymd_of(date)
        m = self.marks[bisect.bisect_right(self.marks, k) - 1]
        hb = self.hb_vid(date)
        if isinstance(hb, str) and "@" in hb:
            hm = int(hb.split("@")[1]) or int(hb.split("@")[0]) * 10000 + 101
        else:
            hm = int(hb) * 10000 + 101
        return f"cs@{max(m, min(hm, k))}"

    @staticmethod
    def parse(vid: str) -> HDate:
        m = int(vid.split("@")[1])
        return HDate(m // 10000, (m // 100) % 100, m % 100)

    def row_geom(self, key, rec):
        if key not in self._g:
            self._g[key] = make_valid(shape(rec["geom"]))
        return self._g[key]

    def _simp(self, fid, g):
        """HB 剩余部分计算用的简化几何（只用于判断 CShapes 覆盖范围，不用于显示）。"""
        key = (fid, id(g))
        r = self._simp_cache.get(key)
        if r is None or r[0] is not g:
            r = (g, g.simplify(0.05) if g.area > 0.2 else g)
            self._simp_cache[key] = r
        return r[1]

    def _apply_fronts(self, k, feats, origin, notes):
        W = self.war
        for ti, si in W.active_steps(k):
            t = W.theatres[ti]
            st = t["steps"][si]
            A = W.theatre_area(ti, si, k)
            bb = box(*t["bbox"])
            n = 0
            for fid in sorted(feats):
                f = feats[fid]
                if fid >= 380000 or not f["geom"].intersects(bb):
                    continue
                pr = f["props"]
                nm = pr.get("NAME")
                if (t.get("targets") and nm not in t["targets"]) or nm in t.get("not_targets", []):
                    continue
                if "SIDE" in pr:
                    sd = pr["SIDE"]
                else:
                    sd = W.side_gw(t, pr.get("CSHAPES"), nm, k)
                if sd not in ("axis", "allied"):
                    continue
                g = f["geom"]
                piece = make_valid(g.intersection(A)) if sd == "allied" else make_valid(g.intersection(bb).difference(A))
                piece = W.polys(piece)
                if piece is None or piece.area < 0.02:
                    continue
                held = "axis_held" if sd == "allied" else "allied_held"
                lab = W.label(t, held, nm, piece, k)
                if lab is None:
                    continue
                rest = W.polys(make_valid(g.difference(piece)))
                if rest is None:
                    del feats[fid]
                else:
                    feats[fid] = {"props": {**pr, "CLIPPED": True}, "geom": rest}
                nf = 380000 + ti * 1000 + n
                n += 1
                nz = pr.get("NAME_ZH") or (W.snames.get(nm) or {}).get("zh") or nm
                feats[nf] = {"props": {"fid": nf, "NAME": f"{nm} ({held})", "LABEL_ZH": lab["zh"].replace("{name}", nz), "QID": lab["qid"],
                                       "FRONT": t["name_zh"], "FRONT_STEP": st.get("label"), "FRONT_PRECISION": st.get("precision") or t.get("precision"),
                                       "FRONT_SRC": st.get("sources", []) + t.get("sources", []), "BORDERPRECISION": 1, "SIDE": "axis" if held == "axis_held" else "allied"},
                             "geom": piece}
                origin[nf] = ("q", lab["qid"])
            notes.append(f"{t['name_zh']}：{st.get('label')}（{st.get('precision') or t.get('precision')}）")

    def _cache_key(self):
        if getattr(self, "_ck", None) is None:
            import hashlib
            from pathlib import Path
            from . import config
            h = hashlib.sha1()
            here = Path(__file__).parent
            files = [here / "cshapes.py", here / "ww2.py", here / "transitions.py"]
            for pat in ("cshapes.json*", "ww2_europe.json*", "transitions.json*", "control_zones.json*", "curated/war_fronts_hist.json"):
                files += sorted(Path(config.DATA_DIR).glob(pat))
            for f in files:
                try:
                    st = f.stat()
                    h.update(f"{f.name}:{st.st_size}:{int(st.st_mtime)}".encode())
                except OSError:
                    pass
            self._ck = h.hexdigest()[:12]
            self._cdir = Path(config.USER_DATA_DIR) / "cache" / "cs_compose" / self._ck
        return self._ck

    @locked_lru(maxsize=24)
    def compose(self, vid: str):
        """-> (features {fid: {props, geom}}, origin {fid: (snap, fid)}, notes)；结果按数据版本缓存到用户数据目录"""
        import pickle
        self._cache_key()
        fp = self._cdir / (vid.replace("@", "_") + ".pkl")
        try:
            if fp.exists():
                with open(fp, "rb") as fh:
                    res = pickle.load(fh)
                for f in res[0].values():
                    prepare(f["geom"])
                return res
        except Exception:
            pass
        res = self._compose(vid)
        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            tmp = fp.with_suffix(".tmp")
            with open(tmp, "wb") as fh:
                pickle.dump(res, fh, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(fp)
        except Exception:
            pass
        return res

    def _compose(self, vid: str):
        date = self.parse(vid)
        k = ymd_of(date)
        feats, origin, notes = {}, {}, []
        for r in self.rows:
            if r["from"] <= k and (r["to"] is None or k < r["to"]):
                fid = OFF_ROW + r["i"]
                feats[fid] = {"props": {"fid": fid, "NAME": r["name"], "CSHAPES": r["gw"], "STATUS": r["status"],
                                        "STATUS_ZH": STATUS_ZH.get(r["status"]), "OWNER": r.get("owner") if r["status"] != "independent" else None,
                                        # 711 是西藏。那条线是数据集轮廓，不是实测边界，面板按「大致」显示。
                                        "BORDERPRECISION": 1 if r.get("gw") == 711 else (3 if r.get("b_def") else 2), "SRC": "CShapes 2.0"},
                              "geom": self.row_geom(("r", r["i"]), r)}
                origin[fid] = ("cs", r["i"])
        def cut(g, keep=()):
            for fid in list(feats):
                if fid in keep:
                    continue
                f = feats[fid]
                if f["geom"].intersects(g):
                    ng = make_valid(f["geom"].difference(g))
                    if ng.is_empty:
                        del feats[fid]
                    else:
                        feats[fid] = {"props": {**f["props"], "CLIPPED": True}, "geom": ng}
        W = self.war
        md = W.stan_month(k)
        if md:
            sf = [(kk, f, W.stan_geom(f[4])) for kk, f in W.stan_feats(md)]
            sg = [g for _, _, g in sf]
            st_tree = STRtree(sg)
            for fid in list(feats):
                g = feats[fid]["geom"]
                idx = st_tree.query(g, predicate="intersects")
                if len(idx) == 0:
                    continue
                ck = (fid, tuple(sorted(sf[i][1][4] for i in idx)))
                if ck not in self._cut_cache:
                    r = _local_diff(g, st_tree, sg)
                    if r is not None and (r.area < 0.3 or r.buffer(-0.15).is_empty):
                        r = None
                    self._cut_cache[ck] = r
                rest = self._cut_cache[ck]
                if rest is None:
                    del feats[fid]
                else:
                    feats[fid] = {"props": {**feats[fid]["props"], "CLIPPED": True}, "geom": rest}
            for kk, f, g in sf:
                fid = OFF_STAN + kk
                nm, st, hos, exile, _ = f
                feats[fid] = {"props": {"fid": fid, "NAME": nm, "NAME_ZH": (W.snames.get(nm) or {}).get("zh"), "WW2_STATUS": st,
                                        "WW2_STATUS_ZH": W.status_zh(st), "HEAD": hos or None, "EXILE": exile or None,
                                        "SIDE": W.side(nm, st, k), "BORDERPRECISION": 2,
                                        "SRC": f"Stanford「Building the New Order」{md // 10000}-{(md // 100) % 100:02d} 月末快照"}, "geom": g}
                origin[fid] = ("ww2", (md, kk))
            notes.append(f"欧洲边界：Stanford Spatial History Lab「Building the New Order: 1938-1945」{md // 10000}-{(md // 100) % 100:02d}-{md % 100:02d} 快照（只记录吞并与新设实体；军事占领线另见战线说明）")
        for j, e in enumerate(self.extras):
            if (e.get("from") is None or e["from"] <= k) and (e.get("to") is None or k < e["to"]):
                g = self.row_geom(("x", j), e)
                cut(g)
                fid = OFF_EXTRA + j
                feats[fid] = {"props": {"fid": fid, "NAME": e["name"], "NAME_ZH": e.get("name_zh"), "QID": e["qid"], "SRC": e.get("src"),
                                        "BORDERPRECISION": 2 if e.get("approx") else 3, "APPROX": e.get("approx")}, "geom": g}
                origin[fid] = ("csx", j)
        # 特殊地位领土（与过渡层同一份数据）
        T = self.store.trans
        dk = date.key()
        for i, t in enumerate(T.terr):
            if not ((t.get("from") is None or tkey(t["from"]) <= dk) and (t.get("to") is None or dk < tkey(t["to"]))):
                continue
            if t.get("only_snaps") and not t.get("cs_ok"):
                continue
            g = T._terr_geom(i)
            if t.get("augment"):
                tgt = [fid for fid, f in feats.items() if f["props"].get("NAME") == t["augment"]]
                if tgt:
                    cut(g, keep=tgt)
                    f = feats[tgt[0]]
                    feats[tgt[0]] = {"props": f["props"], "geom": make_valid(f["geom"].union(g))}
                    notes.append(t["label"])
                continue
            cut(g)
            fid = OFF_TERR + i
            feats[fid] = {"props": {"fid": fid, "NAME": t["name"], "NAME_ZH": t.get("name_zh"), "SUBJECTO": t.get("sov_name"),
                                    "TERRITORY": t["id"], "TERR_CAT": t.get("cat"), "ZONE": t.get("zone"),
                                    "BORDERPRECISION": t.get("precision") or (1 if t.get("cat") == "unverified" else 3)}, "geom": g}
            origin[fid] = ("terr", i)
        self._apply_fronts(k, feats, origin, notes)
        # CShapes 没有覆盖的地区：historical-basemaps 过渡快照裁掉 CShapes 范围后的剩余部分
        # 覆盖范围只取 CShapes 行 + 补充 + 特殊领土（战时切分不改变总覆盖），按候选集合缓存
        ckeys = [("r", r["i"]) for r in self.rows if r["from"] <= k and (r["to"] is None or k < r["to"])]
        ckeys += [("x", j) for j, e in enumerate(self.extras) if (e.get("from") is None or e["from"] <= k) and (e.get("to") is None or k < e["to"])]
        cg = [self._simp(ck, self.row_geom(ck, self.rows[ck[1]] if ck[0] == "r" else self.extras[ck[1]])) for ck in ckeys]
        for fid in feats:
            if OFF_TERR <= fid < OFF_TERR + 100000:
                ckeys.append(("t", fid)); cg.append(self._simp(("t", fid), feats[fid]["geom"]))
        c_tree = STRtree(cg)
        hb = self.hb_vid(date)
        for fid, f in self.store.features(hb).items():
            if fid >= OFF_TERR:
                continue
            g = f["geom"]
            idx = c_tree.query(g, predicate="intersects")
            hk = (hb, fid, tuple(sorted(ckeys[i] for i in idx)))
            if hk not in self._hb_cache:
                gs = g.simplify(0.02) if g.area > 0.5 else g
                rest = _local_diff(gs, c_tree, cg)
                if rest is not None:
                    a0 = gs.area
                    if not (rest.area >= 0.5 * a0 or (rest.area > 1.0 and not rest.buffer(-0.15).is_empty)):
                        rest = None
                self._hb_cache[hk] = rest
            rest = self._hb_cache[hk]
            if rest is None:
                continue
            feats[fid] = {"props": {**f["props"], "SRC": "historical-basemaps（CShapes 未覆盖的部分）"}, "geom": rest}
            origin[fid] = self.store.origin(hb, fid)
        for f in feats.values():
            prepare(f["geom"])
        notes.insert(0, f"边界：CShapes 2.0（{date.y}-{date.m:02d}-{date.d:02d} 起的法理边界）；CShapes 未覆盖的地区用 historical-basemaps {self.store.base_of(hb)} 年快照")
        return feats, origin, notes
