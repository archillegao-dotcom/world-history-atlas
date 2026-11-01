"""
在线获取并本地缓存：维基百科条目摘要（REST /page/summary，中文优先，用 zh-cn 简体变体，否则英文）
与 Wikidata 实体（用于人物页面的「担任职务」等）。
缓存目录：USER_DATA_DIR/wiki_cache/，缓存 30 天；没有网络时返回缓存或 None（界面显示「离线」）。
只用标准库，便于打包。
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request

from .. import config

UA = "WorldHistoryAtlas/0.3 (offline educational history atlas) python-urllib"
TTL = 30 * 86400
CACHE = config.USER_DATA_DIR / "wiki_cache"


def _cache_file(key: str):
    return CACHE / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")


def _get_json(url: str, headers: dict | None = None, key: str | None = None):
    f = _cache_file(key or url)
    if f.exists() and time.time() - f.stat().st_mtime < TTL:
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        with urllib.request.urlopen(req, timeout=15) as r:
            js = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        js = {"_error": e.code}
    except Exception:
        # 离线：有旧缓存就用旧的
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(js, ensure_ascii=False), encoding="utf-8")
    return js


def summary(zh_title: str | None, en_title: str | None) -> dict | None:
    """返回 {"lang","title","extract","thumb","url"}；中文条目优先（简体），否则英文。"""
    for lang, title, hdr in (("zh", zh_title, {"Accept-Language": "zh-cn"}), ("en", en_title, {})):
        if not title:
            continue
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
        js = _get_json(url, hdr, key=f"sum:{lang}:{title}")
        if js and js.get("extract"):
            return {"lang": lang, "title": js.get("title") or title, "extract": js["extract"],
                    "thumb": (js.get("thumbnail") or {}).get("source"),
                    "url": ((js.get("content_urls") or {}).get("desktop") or {}).get("page")
                    or f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"}
    return None


def first_sentence(text: str | None) -> str | None:
    """中文取到第一个「。」，英文取到第一个 '. '。"""
    if not text:
        return None
    for sep in ("。", ". "):
        i = text.find(sep)
        if 0 < i < 400:
            return text[:i + len(sep)].strip()
    return text[:300]


def entities(ids: list[str], props: str = "labels|claims|sitelinks|descriptions") -> dict:
    """批量获取 Wikidata 实体（≤50），带缓存。"""
    out = {}
    for k in range(0, len(ids), 50):
        chunk = ids[k:k + 50]
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(chunk), "props": props,
            "languages": "zh-cn|zh-hans|zh|zh-hant|en", "sitefilter": "zhwiki|enwiki", "format": "json"})
        js = _get_json(url, key=f"ent:{props}:{'|'.join(chunk)}")
        if js:
            out.update(js.get("entities", {}))
    return out


def commons_thumb(filename: str | None, width: int = 320) -> str | None:
    if not filename:
        return None
    fn = urllib.parse.unquote(filename.rsplit("/", 1)[-1]).replace(" ", "_")  # 也接受完整的 Special:FilePath 链接
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(fn)}?width={width}"
