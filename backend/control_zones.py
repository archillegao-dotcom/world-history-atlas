"""实际控制区（data/curated/control_zones.json → tools/build_control_zones.py → data/control_zones.json.gz）的日期工具与加载。
日期语义：from 当日起有效；until 为控制结束（换手）日，当日起无效；只写到月/年的 until 显示到该月/年末。"""
from __future__ import annotations

from .datafile import read_json
from .timeutil import rec_key


def parse(s: str | None, end: bool = False) -> dict | None:
    """'1950-05-01' / '1955-02' / '1912' → {y, m, d, p}；end=True 时把只到月/年的日期换成下一个月/年的第一天（排他上界）。"""
    if not s:
        return None
    neg = s.startswith("-")
    parts = (s[1:] if neg else s).split("-")
    y = int(parts[0]) * (-1 if neg else 1)
    m = int(parts[1]) if len(parts) > 1 else 0
    d = int(parts[2]) if len(parts) > 2 else 0
    if end and not d:
        if m:
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        else:
            y, m = y + 1, 1
        return {"y": y, "m": m, "d": 1, "p": 11}
    # 只到月/年的起始日期取该月/年的第一天（区间从头算起）；p 保留原精度
    return {"y": y, "m": m or 1, "d": d or 1, "p": 11 if d else (10 if m else 9)}


def active(z: dict, dk: float) -> bool:
    a, b = parse(z.get("from")), parse(z.get("until"), end=True)
    return (a is None or rec_key(a) <= dk) and (b is None or dk < rec_key(b))


def load(data_dir) -> list[dict]:
    return (read_json(data_dir / "control_zones.json.gz", {}) or {}).get("zones", [])
