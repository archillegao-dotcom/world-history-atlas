"""
极简 MediaWiki wikitext 清理工具：把一行 wikitext 变成纯文本，同时收集内部链接目标与外部来源链接。
只做显示需要的最小处理，不追求完整解析。
"""
from __future__ import annotations

import html
import re

_REF_SELF = re.compile(r"<ref[^>/]*/>", re.I)
_REF = re.compile(r"<ref[^>]*>.*?</ref>", re.I | re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_EXT = re.compile(r"\[(https?://[^\s\]]+)\s*([^\]]*)\]")
_LINK = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]*))?\]\]")
_TPL = re.compile(r"\{\{([^{}]*)\}\}")


def _template(m: re.Match) -> str:
    """少数常见模板保留文字内容，其余删除。"""
    parts = [p.strip() for p in m.group(1).split("|")]
    name = parts[0].lower().strip()
    args = [p for p in parts[1:] if "=" not in p]
    if name in ("nowrap", "nobr", "small", "lang-en", "noflag", "transl", "sic") and args:
        return args[-1]
    if name.startswith("lang") and len(args) >= 2:
        return args[-1]
    if name in ("convert", "cvt") and len(args) >= 2:
        return f"{args[0]} {args[1]}"
    if name in ("ndash", "snd", "spaced ndash"):
        return " – "
    if name in ("mdash", "spaced mdash"):
        return " — "
    if name in ("as of",) and args:
        return "as of " + " ".join(args)
    return ""


def clean(line: str) -> tuple[str, list[str], list[dict]]:
    """返回 (纯文本, 内部链接目标列表, 外部来源 [{url,label}])。"""
    s = _COMMENT.sub("", line)
    s = _REF.sub("", _REF_SELF.sub("", s))
    for _ in range(4):  # 由内向外去掉嵌套模板
        s2 = _TPL.sub(_template, s)
        if s2 == s:
            break
        s = s2
    sources = []

    def ext(m):
        label = m.group(2).strip().strip("()").replace("''", "").strip() or "source"
        sources.append({"url": m.group(1), "label": label})
        return ""

    s = _EXT.sub(ext, s)
    links: list[str] = []

    def lnk(m):
        target = m.group(1).strip()
        if re.match(r"^(file|image|category|media):", target, re.I):
            return ""
        label = m.group(2) if m.group(2) is not None else target
        t = target.split("#")[0].strip()
        if t:
            links.append(t[0].upper() + t[1:].replace("_", " "))
        return label

    s = _LINK.sub(lnk, s)
    s = s.replace("'''", "").replace("''", "")
    s = _TAG.sub("", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip(" *:;")
    return s, links, sources
