"""
过渡层：在两张边界快照之间，按**真实日期**修正地图。

historical-basemaps 的快照很稀疏（如 1945 → 1960 → 1994），两张快照之间的变化原本不会显示（例如 1950 年仍用 1945 年的
「China」多边形）。本模块在所选日期把以下修正叠加到「不晚于该日期的最近快照」上，得到一张**过渡快照**：

1. inception（成立）：下一张快照里某个政权（如 中华人民共和国）的 Wikidata 成立日期（P571，精确到月或日）落在两张快照之间，
   而上一张快照里还没有它 → 从成立日起，用下一张快照中该政权的多边形覆盖上一张快照的对应区域。
2. dissolution（解散）：上一张快照里某多边形对应的政权全部在两张快照之间解散（P576，精确到月或日，如 苏联 1991-12-26、
   东德/西德 1990-10-03）→ 从解散日起，该区域改用下一张快照的多边形（按原区域裁剪）。
3. overlay（特殊地位领土）：香港、澳门、格陵兰、波多黎各……用 Natural Earth 1:10m 几何从所在多边形中切出，成为可单独点击的区域；
   时间范围取 Wikidata 中该领土及其前身（P1365 链，如 英属香港）的存在期。
4. augment（补充小岛）：1949-12-07（「中华民国(1912–1949)」在 Wikidata 的解散日期，适用于中国大陆）以后，把澎湖、金门、马祖并入台湾多边形。

事件表由 tools/build_transitions.py 生成（data/transitions.json.gz），每条都记录日期来源（Wikidata QID + 属性）。
过渡快照的 ID 形如 "1945@19491001"（基础快照 @ 最近一次修正的日期），多边形 fid：
  < 100000 来自基础快照；100000 + n 来自下一张快照的 fid n；200000 + i 为第 i 个特殊领土。
"""
from __future__ import annotations

from functools import lru_cache

from .geolock import locked_lru

from shapely import make_valid, prepare
from shapely.geometry import shape

from .datafile import read_json
from .timeutil import HDate, rec_key

OFF_NEXT, OFF_TERR = 100000, 200000
MIN_KEEP = 0.02   # 被切剩不足原面积 2% 且面积很小的碎片丢弃


def tkey(t: dict | None) -> float | None:
    return rec_key(t)


def ymd(t: dict) -> int:
    return t["y"] * 10000 + (t.get("m") or 1) * 100 + (t.get("d") or 1)


class Transitions:
    def __init__(self, store, data_dir):
        self.store = store
        d = read_json(data_dir / "transitions.json.gz", {}) or {}
        self.events = d.get("events", [])          # inception / dissolution
        self.terr = d.get("territories", [])       # overlay / augment（含 from/to）
        self._geoms = {}

    # ---------------------------------------------------------------- 选择
    def active(self, base: int, date: HDate):
        dk = date.key()
        ev = [e for e in self.events if e["base"] == base and tkey(e["date"]) <= dk
              and (not e.get("until") or dk <= tkey(e["until"]))]
        tr = [(i, t) for i, t in enumerate(self.terr)
              if (t.get("from") is None or tkey(t["from"]) <= dk) and (t.get("to") is None or dk < tkey(t["to"]))
              and base not in t.get("skip_snaps", []) and (not t.get("only_snaps") or base in t["only_snaps"])]
        return ev, tr

    def vid(self, base: int, date: HDate):
        ev, tr = self.active(base, date)
        if not ev and not tr:
            return base
        dk = date.key()
        marks = [ymd(e["date"]) for e in ev] + [ymd(t["from"]) for _, t in tr if t.get("from")]
        # 有结束日期的修正（如满洲国）结束后，修正集合变化：把已经结束的修正的结束日期也计入标识
        marks += [ymd(e["until"]) for e in self.events if e["base"] == base and e.get("until") and tkey(e["until"]) < dk]
        marks += [ymd(t["to"]) for t in self.terr if t.get("to") and tkey(t["to"]) < dk
                  and base not in t.get("skip_snaps", []) and (not t.get("only_snaps") or base in t["only_snaps"])]
        # 用「已生效的修正」的最晚日期标识过渡快照；同一基础快照内日期相同 ⇒ 修正集合相同
        return f"{base}@{max(marks) if marks else 0}"

    def parse(self, vid: str):
        base, mark = vid.split("@")
        base, mark = int(base), int(mark)
        y, m, d = mark // 10000, (mark // 100) % 100, mark % 100
        if mark == 0:   # 只有不带日期的领土修正
            y, m, d = base, 1, 1
        return base, HDate(y, m, d)

    # ---------------------------------------------------------------- 合成
    def _terr_geom(self, i):
        if i not in self._geoms:
            g = make_valid(shape(self.terr[i]["geom"]))
            self._geoms[i] = g
        return self._geoms[i]

    @locked_lru(maxsize=24)
    def compose(self, vid: str):
        """-> (features {fid: {props, geom}}, origin {fid: (snap, fid)}, notes[list])"""
        base, date = self.parse(vid)
        ev, tr = self.active(base, date)
        src = self.store.features(base)
        feats = {fid: {"props": dict(f["props"]), "geom": f["geom"], "a0": f["geom"].area} for fid, f in src.items()}
        origin = {fid: (base, fid) for fid in feats}
        notes = []

        def cut(g, keep=()):
            for fid in list(feats):
                if fid in keep:
                    continue
                f = feats[fid]
                if f["geom"].intersects(g):
                    ng = make_valid(f["geom"].difference(g))
                    f["geom"] = ng
                    f["props"]["CLIPPED"] = True
                    if ng.is_empty or (ng.area < MIN_KEEP * f["a0"] and ng.area < 0.5):
                        del feats[fid]

        for e in sorted(ev, key=lambda e: tkey(e["date"])):
            nxt = self.store.features(e["src"])
            if e["kind"] == "inception":
                f2 = nxt.get(e["fid"])
                if not f2:
                    continue
                nf = OFF_NEXT + e["fid"]
                if nf in feats:
                    continue
                cut(f2["geom"])
                feats[nf] = {"props": {**f2["props"], "fid": nf, "TRANS": e["label"]}, "geom": f2["geom"], "a0": f2["geom"].area}
                origin[nf] = (e["src"], e["fid"])
            elif e["kind"] == "dissolution":
                f1 = feats.pop(e["fid"], None)
                if not f1:
                    continue
                region = f1["geom"]
                for fid2, f2 in nxt.items():
                    if not f2["geom"].intersects(region):
                        continue
                    piece = make_valid(f2["geom"].intersection(region))
                    if piece.is_empty or piece.area < 0.02 * min(region.area, f2["geom"].area):
                        continue
                    nf = OFF_NEXT + fid2
                    if nf in feats:
                        feats[nf]["geom"] = make_valid(feats[nf]["geom"].union(piece))
                    else:
                        feats[nf] = {"props": {**f2["props"], "fid": nf, "TRANS": e["label"]}, "geom": piece, "a0": piece.area}
                        origin[nf] = (e["src"], fid2)
            notes.append(e["label"])
        for i, t in tr:
            g = self._terr_geom(i)
            if t.get("augment"):
                tgt = [fid for fid, f in feats.items() if f["props"].get("NAME") == t["augment"]]
                if not tgt:
                    continue
                cut(g, keep=tgt)
                for fid in tgt[:1]:
                    feats[fid]["geom"] = make_valid(feats[fid]["geom"].union(g))
                notes.append(t["label"])
                continue
            nf = OFF_TERR + i
            cut(g)
            feats[nf] = {"props": {"fid": nf, "NAME": t["name"], "NAME_ZH": t.get("name_zh"), "SUBJECTO": t.get("sov_name"),
                                   "TERRITORY": t["id"], "TERR_CAT": t.get("cat"), "ZONE": t.get("zone"),
                                   "BORDERPRECISION": t.get("precision") or (1 if t.get("cat") == "unverified" else 3)}, "geom": g, "a0": g.area}
            origin[nf] = ("terr", i)
        for f in feats.values():
            prepare(f["geom"])
        return feats, origin, notes
