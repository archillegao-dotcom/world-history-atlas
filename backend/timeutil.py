"""
日期工具。全应用统一使用「历史纪年」整数年份：-1 = 公元前1年，没有公元0年。
日期用 (year, month, day) 表示；month/day 为 0 表示未知（精度只到年/月）。
为了比较与计算距离，转换成一个连续的「天文日序」浮点数（年*372 + 月*31 + 日，足够排序与粗略距离）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HDate:
    y: int
    m: int = 0
    d: int = 0

    @property
    def astro_year(self) -> int:
        """天文纪年（公元前1年 = 0），用于做减法。"""
        return self.y + 1 if self.y < 0 else self.y

    def key(self) -> float:
        """连续数值，单位约等于「年」。未知月日取年中/月中。"""
        m = self.m if self.m else 6.5
        d = self.d if self.d else (15 if self.m else 0)
        return self.astro_year + (m - 1) / 12 + (d / 372 if d else 0)

    def label_zh(self) -> str:
        base = f"公元前{-self.y}年" if self.y < 0 else f"{self.y}年"
        if self.m:
            base += f"{self.m}月"
            if self.d:
                base += f"{self.d}日"
        return base


_DATE_RE = re.compile(r"^\s*(-?\d+)(?:-(\d{1,2})(?:-(\d{1,2}))?)?\s*$")


def parse_date(s: str) -> HDate:
    """接受 '1789-07-14'、'1789'、'-221'（=公元前221年）、'-500-03'。"""
    m = _DATE_RE.match(s or "")
    if not m:
        raise ValueError(f"无法解析日期: {s!r}（格式：YYYY[-MM[-DD]]，公元前用负数，如 -221）")
    y = int(m.group(1))
    if y == 0:
        y = -1  # 没有公元0年，按公元前1年处理
    return HDate(y, int(m.group(2) or 0), int(m.group(3) or 0))


def rec_key(t: dict | None) -> float | None:
    """数据文件中的时间对象 {"y","m","d","p"} -> 连续数值。"""
    if not t:
        return None
    return HDate(t["y"], t.get("m", 0), t.get("d", 0)).key()


PRECISION_ZH = {6: "千年", 7: "世纪", 8: "十年", 9: "年", 10: "月", 11: "日"}
