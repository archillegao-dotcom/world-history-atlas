"""
每日新闻：抓取并解析英文维基百科「Portal:Current events」每日页面（约 2002 年中起每天一页），
以及更早年份（1995–2002）年份条目（如「1995」）中 ==Events== 一节按日期列出的事件。

- 定位：条目中的内部链接（如 [[Madagascar]]、[[Fairfield, California]]）与本地地名表
  data/gazetteer.json.gz（Wikidata：英文维基条目名 -> 坐标/QID/中文名）匹配，得到一个或多个坐标；
  点击地图政权时，只要条目的任一坐标落在该政权多边形内就会显示。
- 存储：每年一个文件 current_events/<年>.json.gz（随应用附带的历史数据在 DATA_DIR，
  自动更新写入 USER_DATA_DIR，后者覆盖前者的同一天）。
- 礼仪：MediaWiki API，每次最多 50 个页面，串行、带 User-Agent、间隔 ≥1 秒。
仅用标准库（urllib），便于打包。
"""
from __future__ import annotations

from .. import datafile
from ..datafile import read_json
import datetime as dt
import gzip
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .wikitext import clean

API = "https://en.wikipedia.org/w/api.php"
UA = "WorldHistoryAtlas/0.2 (offline educational history atlas; daily news layer) python-urllib"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
PORTAL_START = dt.date(2002, 7, 1)  # 此前用年份条目


def portal_title(d: dt.date) -> str:
    return f"Portal:Current events/{d.year} {MONTHS[d.month - 1]} {d.day}"


def portal_url(d: dt.date) -> str:
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(portal_title(d).replace(" ", "_"))


def fetch_wikitext(titles: list[str]) -> dict[str, str]:
    """批量获取页面 wikitext（≤50 个标题），返回 {标题: 内容}；不存在的页面不返回。"""
    out = {}
    for k in range(0, len(titles), 50):
        q = urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                                    "format": "json", "formatversion": "2", "redirects": "1",
                                    "titles": "|".join(titles[k:k + 50])})
        req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    js = json.loads(r.read().decode("utf-8"))
                break
            except Exception:  # 网络错误：退避重试
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        for p in js.get("query", {}).get("pages", []):
            if not p.get("missing") and p.get("revisions"):
                out[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
        time.sleep(1.0)
    return out


def _item(date: dt.date, text, links, sources, context, cat, page_url) -> dict:
    h = hashlib.sha1(f"{date}{text}".encode()).hexdigest()[:12]
    return {"id": h, "date": date.isoformat(), "text": text, "links": links, "sources": sources,
            "context": context, "cat": cat, "page": page_url}


def parse_portal(text: str, date: dt.date) -> list[dict]:
    """解析每日页面：分类标题（'''X''' 或 ;X）+ 多级列表；叶子列表项才是一条新闻，祖先项作为「话题」上下文。"""
    i = text.find("All news items below this line")
    if i >= 0:
        text = text[text.find("\n", i) + 1:] if "-->" in text[i:i + 60] else text[i:]
    lines = [ln.rstrip() for ln in text.split("\n")]
    parsed = []  # (depth, line, cat)
    cat = None
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^(?:'''(.+?)'''|;\s*(.+))$", s)
        if m and not s.startswith("*"):
            cat = clean(m.group(1) or m.group(2))[0]
            continue
        m = re.match(r"^(\*+)\s*(.*)$", s)
        if m:
            parsed.append((len(m.group(1)), m.group(2), cat))
    items = []
    stack: list[tuple[int, str, list[str]]] = []
    url = portal_url(date)
    for idx, (depth, raw, c) in enumerate(parsed):
        txt, links, sources = clean(raw)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        nxt = parsed[idx + 1][0] if idx + 1 < len(parsed) else 0
        if nxt > depth:  # 有子项：是话题标题
            stack.append((depth, txt, links))
            continue
        if len(txt) < 15:
            continue
        ctx = [s[1] for s in stack if s[1]]
        ctx_links = [l for s in stack for l in s[2]]
        it = _item(date, txt, links, sources, ctx, c, url)
        it["ctx_links"] = ctx_links
        items.append(it)
    return items


_DAY = re.compile(r"^\[\[(" + "|".join(MONTHS) + r") (\d{1,2})\]\]")


def parse_year_article(text: str, year: int) -> list[dict]:
    """解析年份条目（如 '1998'）的 ==Events== 一节：'* [[January 6]] – 文本' 或 '* [[January 1]]' + '** 文本'。"""
    m = re.search(r"^==\s*Events\s*==\s*$", text, re.M)
    if not m:
        return []
    body = text[m.end():]
    e = re.search(r"^==[^=].*==\s*$", body, re.M)
    body = body[:e.start()] if e else body
    items, cur = [], None
    url = f"https://en.wikipedia.org/wiki/{year}#Events"
    for ln in body.split("\n"):
        s = ln.strip()
        mm = re.match(r"^(\*+)\s*(.*)$", s)
        if not mm:
            continue
        depth, rest = len(mm.group(1)), mm.group(2)
        dm = _DAY.match(rest)
        if depth == 1:
            cur = None
            if dm:
                try:
                    cur = dt.date(year, MONTHS.index(dm.group(1)) + 1, int(dm.group(2)))
                except ValueError:
                    cur = None
                rest = re.sub(r"^\[\[[^\]]+\]\](\s*[–-]\s*\[\[[^\]]+\]\])?\s*[–—-]?\s*", "", rest)
            if cur and rest.strip():
                txt, links, sources = clean(rest)
                if len(txt) >= 15:
                    items.append(_item(cur, txt, links, sources, [], None, url))
        elif cur:
            txt, links, sources = clean(rest)
            if len(txt) >= 15:
                items.append(_item(cur, txt, links, sources, [], None, url))
    return items


# ------------------------------------------------------------------ 定位
class Gazetteer:
    """英文维基条目名 -> [lon, lat, qid, 中文名, sitelinks, 是否国家]"""

    def __init__(self, path: Path):
        self.d = read_json(path, {})

    def locate(self, item: dict) -> None:
        places = []
        for t in item.get("links", []) + item.get("ctx_links", []):
            g = self.d.get(t)
            if g and t not in [p["t"] for p in places]:
                places.append({"t": t, "coord": [g[0], g[1]], "qid": g[2], "zh": g[3], "country": bool(g[5])})
        # 优先城市级（更精确），其后国家；最多 6 个
        places.sort(key=lambda p: p["country"])
        item["places"] = places[:6]
        compact(item)


def compact(item: dict) -> dict:
    """压缩存储格式（数据量大：约 15 万条）：去掉只在定位时需要的链接列表，坐标与来源用短数组。
    places: [[lon, lat, 显示名, 是否国家]]；sources: [[url, label]]（只留第一个；当天维基页面本身列有全部引用）；context 只留最后 2 级。"""
    item.pop("ctx_links", None)
    item.pop("links", None)
    item.pop("page", None)  # 可由日期推出
    if item.get("places") and isinstance(item["places"][0], dict):
        item["places"] = [[p["coord"][0], p["coord"][1], p["zh"] or p["t"], 1 if p["country"] else 0] for p in item["places"]]
    if item.get("sources") and isinstance(item["sources"][0], dict):
        item["sources"] = [[x["url"], x["label"][:40]] for x in item["sources"][:1]]
    item["context"] = item.get("context", [])[-2:]
    if not item.get("cat"):
        item.pop("cat", None)
    return item


def page_url_for(date_iso: str) -> str:
    """条目来源页面：2002-07 起为当日 Portal 页面，此前为年份条目的 Events 一节。"""
    d = dt.date.fromisoformat(date_iso)
    return portal_url(d) if d >= PORTAL_START else f"https://en.wikipedia.org/wiki/{d.year}#Events"


# ------------------------------------------------------------------ 存储
def load_year(dirs: list[Path], year: int) -> dict[str, list[dict]]:
    """合并多个目录中同一年的数据：后面的目录（用户可写目录）覆盖前面的同一天。"""
    days: dict[str, list[dict]] = {}
    for d in dirs:
        f = d / "current_events" / f"{year}.json.gz"
        if datafile.exists(f):  # .json.xz（随应用附带）或 .json.gz（自动更新写入）
            days.update(read_json(f, {}))
    return days


def save_year(base: Path, year: int, days: dict[str, list[dict]]) -> None:
    f = base / "current_events" / f"{year}.json.gz"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(days, ensure_ascii=False, separators=(",", ":")).encode()))
    tmp.replace(f)


def fetch_days(dates: list[dt.date], gaz: Gazetteer, log=print) -> dict[str, list[dict]]:
    """抓取若干天的每日页面（2002-07 之前的日期改用年份条目），返回 {日期: [条目]}。"""
    out: dict[str, list[dict]] = {}
    portal = [d for d in dates if d >= PORTAL_START]
    titles = {portal_title(d): d for d in portal}
    for k in range(0, len(portal), 50):
        chunk = [portal_title(d) for d in portal[k:k + 50]]
        texts = fetch_wikitext(chunk)
        for t, txt in texts.items():
            d = titles.get(t)
            if d:
                its = parse_portal(txt, d)
                for it in its:
                    gaz.locate(it)
                out[d.isoformat()] = its
        log(f"   current events: {portal[k]} .. {portal[min(k + 49, len(portal) - 1)]}: {sum(len(out.get(x.isoformat(), [])) for x in portal[k:k + 50])} items")
    for y in sorted({d.year for d in dates if d < PORTAL_START}):
        txt = fetch_wikitext([str(y)]).get(str(y), "")
        wanted = {d.isoformat() for d in dates if d.year == y and d < PORTAL_START}
        for it in parse_year_article(txt, y):
            if it["date"] in wanted:
                gaz.locate(it)
                out.setdefault(it["date"], []).append(it)
        log(f"   year article {y}: {sum(len(v) for k2, v in out.items() if k2.startswith(str(y)))} items")
    return out


def update(base_dirs: list[Path], write_dir: Path, gaz: Gazetteer, start: dt.date, end: dt.date, log=print) -> int:
    """抓取 [start, end] 的每一天并写入 write_dir；返回条目数。"""
    dates = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    got = fetch_days(dates, gaz, log)
    n = 0
    for y in sorted({d.year for d in dates}):
        days = load_year([write_dir], y)
        for k, v in got.items():
            if k.startswith(f"{y:04d}-"):
                days[k] = v
                n += len(v)
        save_year(write_dir, y, days)
    return n
