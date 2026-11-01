"""
政权解析：地图多边形（快照, fid）+ 日期 → Wikidata 政权。

数据：
  data/polity_map.json.gz  每个多边形的候选政权（名称匹配 / 首都在多边形内 / 自身坐标在内），见 tools/build_polity_map.py
  data/states.json.gz      政权详情（存在期、首都、政体、元首、首脑……）
  data/offices.json.gz     职位与任职者；data/persons.json.gz 人物；data/orgs.json.gz 机构

resolve() 返回所选日期「存在」的候选（存在期包含该日期；缺失的端点视为开放），按分数排序。
第一个作为「主要政权」，其余作为「同一地区当时的其他政权」供用户切换。
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from .datafile import read_json
from .timeutil import HDate, rec_key


def _load(path: Path, default):
    return read_json(path, default)


def valid_at(dk: float, a: dict | None, b: dict | None, slack: float = 0.0) -> bool:
    ka, kb = rec_key(a), rec_key(b)
    return (ka is None or ka - slack <= dk) and (kb is None or dk <= kb + slack)


STRONG = {"naturalearth", "wiki-title", "name", "capital+name", "coord+name"}
NOW_KEY = 2100.0


def _slack(t: dict | None) -> float:
    """只精确到年（或更粗）的端点允许 1 年误差；精确到月/日的端点不放宽。"""
    return 1.0 if t and not t.get("m") else 0.0


def alive(dk: float, s: dict) -> bool:
    ka, kb = rec_key(s.get("from")), rec_key(s.get("to"))
    return (ka is None or ka - _slack(s.get("from")) <= dk) and (kb is None or dk <= kb + _slack(s.get("to")))


class PolityResolver:
    def __init__(self, data_dir: Path):
        self.map = _load(data_dir / "polity_map.json.gz", {})
        self.states = {s["id"]: s for s in _load(data_dir / "states.json.gz", [])}
        self.offices = _load(data_dir / "offices.json.gz", [])
        self.persons = {p["id"]: p for p in _load(data_dir / "persons.json.gz", [])}
        self.orgs = {o["id"]: o for o in _load(data_dir / "orgs.json.gz", [])}
        self.office_by_state: dict[str, list[dict]] = {}
        for o in self.offices:
            for s in o.get("juris", []):
                self.office_by_state.setdefault(s, []).append(o)

    def candidates(self, snap: int, fid: int) -> list[list]:
        return self.map.get(str(snap), {}).get(str(fid), [])

    def resolve(self, snap: int, fid: int, date: HDate, min_score: float = 0) -> list[dict]:
        """所选日期存在的候选政权，排序规则：
        1. 「强」候选（Natural Earth 自带 ID、同名维基条目、名称匹配、首都在内且名称相近）在前；
        2. 强候选中 Natural Earth 优先，其余按存在期由短到长——同一地区同名的多个政权里，
           存在期最短且包含该日期的通常就是当时那个具体政权（如 1938 年的「纳粹德国」而不是「德国」）；
        3. 弱候选（仅首都/坐标落在范围内，常是下级行政区）按分数排在后面。"""
        dk = date.key()
        out = []
        for qid, method, score in self.candidates(snap, fid):
            s = self.states.get(qid)
            if not s or score < min_score:
                continue
            if alive(dk, s):
                out.append({"state": s, "method": method, "score": score, "strong": method in STRONG})

        def span(c):
            a, b = rec_key(c["state"].get("from")), rec_key(c["state"].get("to"))
            return (b if b is not None else NOW_KEY) - (a if a is not None else -1e5)

        out.sort(key=lambda c: (not c["strong"], c["method"] != "naturalearth",
                                span(c) if c["strong"] else 0, -c["score"]))
        return out

    def strong(self, snap: int, fid: int, date: HDate) -> list[dict]:
        return [c for c in self.resolve(snap, fid, date) if c["strong"]]

    def state_name(self, qid: str) -> str:
        s = self.states.get(qid) or self.persons.get(qid) or {}
        return s.get("zh") or s.get("en") or qid

    def person_brief(self, pid: str) -> dict:
        p = self.persons.get(pid, {})
        return {"id": pid, "name": p.get("zh") or p.get("en") or pid, "en": p.get("en"), "desc": p.get("desc"),
                "born": p.get("born"), "died": p.get("died")}


