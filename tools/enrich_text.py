#!/usr/bin/env python3
"""
中文化与条约简介补全（在所有 build_*.py 之后运行；可重复运行、断点续跑）。

1. 条约/阵营简介：有中文维基条目 → 取 zh.wikipedia 导言（variant=zh-cn，简体）；否则取 en.wikipedia 导言并机器翻译，
   标注「（机器翻译）」，同时保留英文原文与条目链接。维基百科 API（action=query&prop=extracts&exintro），
   每批 20 个条目、每批间隔 1 秒，结果缓存在 data/cache/wiki_leads.json.gz。
2. 名称与描述：Wikidata 没有中文标签（也没有中文维基条目名）的政权、职位、条约、阵营、资源点、机构、城市、事件、人物，
   用离线机器翻译（Argos Translate 英→中模型，CTranslate2 推理，无需 API key）翻译，名称标注「（译名）」，
   描述标注「（机器翻译）」；原英文保存在 en / desc_en 字段。翻译缓存：data/cache/mt_en_zh.json.gz。
用法：/workspace/mtvenv/bin/python tools/enrich_text.py [--no-wiki]
（需要 argostranslate 及其 en→zh 模型：pip install argostranslate；argospm install translate-en_zh）
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("WHA_DATA_DIR", ROOT / "data"))
CACHE = DATA / "cache"
CJK = re.compile(r"[\u4e00-\u9fff]")
UA = "WorldHistoryAtlas/0.5 (offline educational history atlas; contact via project README) python-urllib"
NAME_MARK, DESC_MARK = "（译名）", "（机器翻译）"


def unapply(o):
    """撤销上一次运行写入的机器翻译（使本脚本可重复运行：先还原，再用当前缓存重新套用）。"""
    if isinstance(o, list):
        for x in o:
            unapply(x)
        return o
    if not isinstance(o, dict):
        return o
    if o.get("desc_mt"):
        o["desc"] = o.pop("desc_en", None)
        o.pop("desc_mt")
    if o.get("name_mt"):
        o["name"] = o.get("en_name") or o["name"].replace(NAME_MARK, "")
        o.pop("name_mt")
    for k in [k for k in list(o) if k.endswith("_mt") and o[k] is True and k not in ("desc_mt", "name_mt")]:
        o.pop(k[:-3], None)
        o.pop(k)
    if o.get("mt") is True and "text" in o:            # summary
        o.pop("text"); o.pop("mt")
    for k, v in list(o.items()):
        if isinstance(v, str) and v.endswith(NAME_MARK):
            o.pop(k)
        elif isinstance(v, (dict, list)):
            unapply(v)
    return o


def load(name):
    return unapply(json.loads(gzip.decompress((DATA / name).read_bytes())))


def save(name, obj):
    (DATA / name).write_bytes(gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6))


def load_cache(name):
    p = CACHE / name
    return json.loads(gzip.decompress(p.read_bytes())) if p.exists() else {}


def save_cache(name, obj):
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / name).write_bytes(gzip.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8")))


def has_cjk(s):
    return bool(s and CJK.search(s))


# ------------------------------------------------------------------ 维基百科导言
def fetch_leads(lang, titles, cache):
    todo = [t for t in titles if f"{lang}:{t}" not in cache]
    print(f"wiki {lang}: {len(titles)} titles, {len(todo)} to fetch", flush=True)
    for k in range(0, len(todo), 20):
        chunk = todo[k:k + 20]
        params = {"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "exchars": 600, "exlimit": 20,
                  "titles": "|".join(chunk), "format": "json", "redirects": 1}
        if lang == "zh":
            params["variant"] = "zh-cn"
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        for attempt in range(4):
            try:
                d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60))
                break
            except Exception as e:  # noqa: BLE001
                print("  retry", attempt, e, flush=True)
                time.sleep(5 * (attempt + 1))
        else:
            continue
        q = d.get("query", {})
        back = {}
        for r in q.get("normalized", []) + q.get("redirects", []):
            back[r["to"]] = back.get(r["from"], r["from"])
        for pg in q.get("pages", {}).values():
            t = pg.get("title")
            orig = back.get(t, t)
            while orig in back:
                orig = back[orig]
            cache[f"{lang}:{orig}"] = (pg.get("extract") or "").strip()
        for t in chunk:
            cache.setdefault(f"{lang}:{t}", "")
        if k % 400 == 0:
            save_cache("wiki_leads.json.gz", cache)
        time.sleep(1.0)
    save_cache("wiki_leads.json.gz", cache)


def first_sentences(text, n=2, maxlen=320):
    parts = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    out = " ".join(parts[:n])
    return out[:maxlen]


# ------------------------------------------------------------------ 机器翻译
def worth(s):
    """只翻译含英文单词的文本；纯数字、日期、代号原样保留。"""
    return len(re.findall(r"[A-Za-z]{2,}", s)) >= 1


_BAD = re.compile(r"[\u0600-\u06ff\u0400-\u04ff\u0590-\u05ff⁇]|简体|中文\(|(.)\1{2,}|(..)\2{2,}|(\S{2,})\s+\3")


def plausible(src, out):
    """机器翻译质量把关：明显的乱码/幻觉（夹杂阿拉伯/西里尔字母、重复字串、长度离谱、没有汉字）一律不用，保留英文原文。"""
    if not has_cjk(out) or _BAD.search(out) or "英语" in out or "英文" in out:
        return False
    cjk = len(re.findall(r"[\u4e00-\u9fff]", out))
    words = max(1, len(re.findall(r"[A-Za-z]+", src)))
    if cjk > 4 * words + 8 or cjk < max(1, words // 3):
        return False
    src_words = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", src)}
    if any(w.lower() not in src_words for w in re.findall(r"[A-Za-z]{3,}", out)):   # 译文里冒出原文没有的英文词 = 幻觉
        return False
    if len(src) < 80 and re.search(r"[:：?？!！]$", out) and not re.search(r"[:?!]$", src):
        return False
    return True

CACHE_NAME = "mt_en_zh_f32.json.gz"
_SENT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9(\"'])")


class MT:
    """Argos Translate（OPUS-MT）en→zh 模型，直接用 ctranslate2 批量翻译。
    实测（ctranslate2 4.8.4，本机 CPU）：int8 量化与 inter_threads>1 都会产生大量乱码，
    所以固定 compute_type=float32、inter_threads=1；长文本先按句切分再翻译。"""

    def __init__(self):
        import ctranslate2
        import sentencepiece as spm
        pk = [p for p in glob.glob(os.path.expanduser("~/.local/share/argos-translate/packages/*"))
              if json.load(open(p + "/metadata.json")).get("to_code") == "zh"]
        if not pk:
            sys.exit("未安装 Argos Translate en→zh 模型")
        self.meta = json.load(open(pk[0] + "/metadata.json"))
        self.tr = ctranslate2.Translator(pk[0] + "/model", device="cpu", inter_threads=1, intra_threads=8,
                                         compute_type="float32")
        self.sp = spm.SentencePieceProcessor(model_file=pk[0] + "/sentencepiece.model")
        self.cache = load_cache(CACHE_NAME)     # 句子级缓存
        self.full = {}

    def _clean(self, z):
        return z.replace("▁", "").strip()

    def run(self, texts):
        texts = {t for t in texts if t and worth(t)}
        sents = sorted({x for t in texts for x in _SENT.split(t) if x.strip()} - set(self.cache))
        print(f"MT: {len(texts)} strings, {len(sents)} new sentences", flush=True)
        for k in range(0, len(sents), 256):
            chunk = sents[k:k + 256]
            res = self.tr.translate_batch([self.sp.encode(x, out_type=str)[:200] for x in chunk], max_batch_size=32,
                                          beam_size=4, length_penalty=0.2, replace_unknowns=True, max_decoding_length=300)
            for x, r in zip(chunk, res):
                self.cache[x] = self._clean(self.sp.decode(r.hypotheses[0]))
            if k % 5120 == 0:
                save_cache(CACHE_NAME, self.cache)
                print(f"  {k + len(chunk)}/{len(sents)}", flush=True)
        save_cache(CACHE_NAME, self.cache)

    def _full(self, s):
        parts = [self.cache.get(x) for x in _SENT.split(s) if x.strip()]
        if not parts or any(p is None for p in parts):
            return None
        return "".join(parts)

    def get(self, s):
        z = self._full(s) if s and worth(s) else None
        if not z or not plausible(s, z):
            return None
        return z[:-1] if z.endswith(".") and not s.endswith(".") else z


def name_jobs(recs, zk="zh", ek="en"):
    return [r[ek] for r in recs if not has_cjk(r.get(zk)) and r.get(ek)]


def apply_name(recs, mt, zk="zh", ek="en"):
    n = 0
    for r in recs:
        if r.get(f"{zk}_mt") or has_cjk(r.get(zk)) or not r.get(ek):
            continue
        z = mt.get(r[ek])
        if z and has_cjk(z):
            r[zk] = z + NAME_MARK
            r[f"{zk}_mt"] = True
            n += 1
    return n


def apply_desc(recs, mt):
    n = 0
    for r in recs:
        d = r.get("desc")
        if not d or has_cjk(d) or r.get("desc_mt"):
            continue
        z = mt.get(d)
        if z and has_cjk(z):
            r["desc_en"], r["desc"], r["desc_mt"] = d, z + DESC_MARK, True
            n += 1
    return n


def main():
    no_wiki = "--no-wiki" in sys.argv
    tr = load("treaties.json.gz")
    al = load("alliances.json.gz")
    leads = load_cache("wiki_leads.json.gz")
    if not no_wiki:
        fetch_leads("zh", sorted({r["zhwiki"] for r in tr + al if r.get("zhwiki")}), leads)
        fetch_leads("en", sorted({r["enwiki"] for r in tr + al if r.get("enwiki") and not r.get("zhwiki")}), leads)
    # 简介
    en_sum = []
    for r in tr + al:
        z = leads.get(f"zh:{r.get('zhwiki')}") if r.get("zhwiki") else None
        if z:
            r["summary"] = {"text": first_sentences(z, 3, 300), "src": "zh.wikipedia",
                            "url": "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(r["zhwiki"].replace(" ", "_"))}
        elif r.get("enwiki") and leads.get(f"en:{r['enwiki']}"):
            e = first_sentences(leads[f"en:{r['enwiki']}"], 2, 320)
            r["summary"] = {"en": e, "src": "en.wikipedia",
                            "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(r["enwiki"].replace(" ", "_"))}
            en_sum.append(e)
    sets = {n: load(f"{n}.json.gz") for n in ("states", "offices", "resources", "orgs", "cities", "persons")}
    ev = load("events.json.gz")
    ru = load("rulers.json.gz")
    rp = load("ruler_persons.json.gz")
    texts = en_sum + name_jobs(tr) + name_jobs(al) + name_jobs(ru["offices"]) + name_jobs(rp)
    for recs in sets.values():
        texts += name_jobs(recs)
    texts += [e.get("en_name") or e["name"] for e in ev if not has_cjk(e.get("name")) and (e.get("en_name") or e.get("name"))]
    for recs in [tr, al, ru["offices"], rp, ev] + list(sets.values()):
        texts += [r["desc"] for r in recs if r.get("desc") and not has_cjk(r["desc"])]
    for r in tr:
        texts += [x["en"] for x in r.get("location", []) if x.get("en") and not x.get("zh")]
        texts += [t["en"] for t in r.get("types", []) if t.get("en") and not t.get("zh")]
    for s in sets["states"]:
        texts += [g["en"] for g in s.get("gov", []) + s.get("ideology", []) if g.get("en") and not has_cjk(g.get("zh"))]
    mt = MT()
    mt.run(texts)
    stat = {}
    for r in tr + al:
        sm = r.get("summary")
        if sm and sm.get("en") and not sm.get("text"):
            z = mt.get(sm["en"])
            if z:
                sm["text"], sm["mt"] = z + DESC_MARK, True
    for r in tr:
        for x in r.get("location", []):
            if not x.get("zh") and x.get("en") and mt.get(x["en"]):
                x["zh"], x["zh_mt"] = mt.get(x["en"]) + NAME_MARK, True
        for t in r.get("types", []):
            if not t.get("zh") and t.get("en") and mt.get(t["en"]):
                t["zh"] = mt.get(t["en"]) + NAME_MARK
    for s in sets["states"]:
        for g in s.get("gov", []) + s.get("ideology", []):
            if g.get("en") and not has_cjk(g.get("zh")) and mt.get(g["en"]):
                g["zh"] = mt.get(g["en"]) + NAME_MARK
    for nm, recs in [("treaties", tr), ("alliances", al), ("rulers.offices", ru["offices"]), ("ruler_persons", rp)] + list(sets.items()):
        stat[nm] = {"names": apply_name(recs, mt), "descs": apply_desc(recs, mt)}
    ne = 0
    for e in ev:
        if has_cjk(e.get("name")) or e.get("name_mt"):
            continue
        src = e.get("en_name") or e.get("name")
        z = mt.get(src)
        if z and has_cjk(z):
            e.setdefault("en_name", src)
            e["name"], e["name_mt"] = z + NAME_MARK, True
            ne += 1
    stat["events"] = {"names": ne, "descs": apply_desc(ev, mt)}
    save("treaties.json.gz", tr)
    save("alliances.json.gz", al)
    save("rulers.json.gz", ru)
    save("ruler_persons.json.gz", rp)
    save("events.json.gz", ev)
    for n, recs in sets.items():
        save(f"{n}.json.gz", recs)
    (DATA / "audit").mkdir(exist_ok=True)
    (DATA / "audit" / "enrich_stats.json").write_text(json.dumps({"applied": stat, "mt_model": mt.meta.get("package_version"),
                                                                   "generated": time.strftime("%Y-%m-%d %H:%M")},
                                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stat, ensure_ascii=False))


if __name__ == "__main__":
    main()
