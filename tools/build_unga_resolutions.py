"""从达格·哈马舍尔德图书馆的大会决议表收录大会决议。

常规届、紧急特别届、特别届都读图书馆自己的表。
每条保留文号、单日通过日期、标题、表决原文，并链到联合国正式文件系统。
数字图书馆能对上记录号的写记录链接，对不上的写按文号检索的链接，不补造表决或日期。
输出 data/curated/unga_resolutions.json。不写 diplomacy_acts.json。
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "unga_resolutions.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; world-history-atlas/unga; research)"}

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
DATE_RE = re.compile(
    r"(\d{1,2})(?:\s*[-–—]\s*(\d{1,2}))?\s*([A-Za-z]{3,9})\.?\s*(\d{4})"
)


def fetch(url: str, timeout: int = 60) -> str:
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return raw.decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            time.sleep(1.2 * (i + 1))
    raise RuntimeError(f"{url} {last}")


def cell_text(fragment: str) -> str:
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)<!--.*?-->", " ", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment).replace("\xa0", " ")
    lines = []
    for line in fragment.split("\n"):
        line = re.sub(r"\s+", " ", line).strip(" \t;")
        if line:
            lines.append(line)
    return "\n".join(lines)


def canonical_symbol(href: str) -> str:
    text = urllib.parse.unquote(href or "")
    # 文号里可以再有斜杠（A/RES/68/262、A/RES/ES-11/4）。& 之后是链接参数，不是文号。
    match = re.search(r"A/RES/([0-9A-Za-z().\-]+(?:/[0-9A-Za-z().\-]+)*)", text, re.I)
    if not match:
        return ""
    return "A/RES/" + match.group(1)


def absolute_doc(href: str) -> str:
    href = html.unescape((href or "").strip())
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("http://"):
        href = "https://" + href[len("http://"):]
    return href.split("#", 1)[0]


def valid_iso(year: int, month: int, day: int) -> str | None:
    if not (1946 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    try:
        import datetime
        datetime.date(year, month, day)
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_date(text: str) -> tuple[str | None, str, str]:
    """返回 (iso 或空, 原因, 日期原文)。多个日期或区间不猜单日。"""
    if re.search(r"\d{1,2}\s+[A-Za-z]{3,9}\.?\s*[-–—]\s*\d{1,2}\s+[A-Za-z]{3,9}", text or ""):
        raw = re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()
        return None, "通过日期是区间，不写成单日", raw
    found = list(DATE_RE.finditer(text or ""))
    if not found:
        return None, "通过日期无记录", ""
    if len(found) > 1:
        raw = "；".join(m.group(0) for m in found)
        return None, "通过日期不止一个，不选取单日", raw
    match = found[0]
    raw = match.group(0)
    mon = MONTHS.get(match.group(3).lower())
    if not mon:
        return None, "月份无记录", raw
    if match.group(2):
        return None, "通过日期是区间，不写成单日", raw
    iso = valid_iso(int(match.group(4)), mon, int(match.group(1)))
    if not iso:
        return None, "通过日期无法换算", raw
    return iso, "", raw


def vote_zh(lines: list[str]) -> tuple[str, str]:
    if not lines:
        return "无", ""
    raw = "；".join(lines)
    low = raw.lower()
    parts: list[str] = []
    tally = re.search(r"(\d+)\s*[-–—]\s*(\d+)\s*[-–—]\s*(\d+)", raw)
    if tally:
        yes, no, abstain = (str(int(tally.group(i))) for i in (1, 2, 3))
        parts.append(f"{yes}票赞成、{no}票反对、{abstain}票弃权（{yes}-{no}-{abstain}）")
    words = re.search(
        r"(\d+)\s+votes?\s+to\s+(\d+).*?(\d+)\s+abstention",
        low,
    )
    if words and not tally:
        parts.append(f"{int(words.group(1))}票赞成、{int(words.group(2))}票反对、{int(words.group(3))}票弃权")
    if re.search(r"without\s+(a\s+)?vote", low):
        parts.append("未经表决")
    if "unanimous" in low:
        parts.append("一致通过")
    if "consensus" in low:
        parts.append("协商一致")
    if re.search(r"non[-\s]?recorded", low):
        parts.append("非记录表决")
    if re.search(r"recorded vote", low) and not tally and not words:
        parts.append("记录表决")
    if not parts:
        return "原文：" + raw, raw
    seen = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return "；".join(seen), raw


def vote_lines(cell: str, date_raw: str) -> list[str]:
    if not cell:
        return []
    idx = cell.find(date_raw) if date_raw else -1
    after = cell[idx + len(date_raw):] if idx >= 0 else cell
    lines = []
    for line in after.split("\n"):
        line = line.strip(" ;,.")
        if not line:
            continue
        if re.match(r"^(A|S|E)/", line) or re.match(r"^GA/\d", line) or re.match(r"^A/PV", line):
            continue
        if DATE_RE.search(line):
            continue
        lines.append(line)
    return lines


def meeting_of(cell: str) -> str:
    match = re.search(r"\b((?:A|S)/[A-Z0-9./-]*PV[A-Z0-9./-]*)", cell or "")
    if match:
        return match.group(1)
    match = re.search(r"\b(A/PV\.\d+[A-Za-z0-9./-]*)", cell or "")
    return match.group(1) if match else ""


def resolution_link(chunk: str) -> tuple[str, str] | None:
    for match in re.finditer(r"(?is)<a\b([^>]*?)>", chunk):
        href_match = re.search(r'(?is)href\s*=\s*"([^"]+)"', match.group(1))
        if not href_match:
            href_match = re.search(r"(?is)href\s*=\s*'([^']+)'", match.group(1))
        if not href_match:
            continue
        href = href_match.group(1)
        if not re.search(r"A/RES/", urllib.parse.unquote(href), re.I):
            continue
        rest = chunk[match.end():]
        stop = re.search(r"(?is)</a>|<a\b|<td\b|</td>|<tr\b", rest)
        inner = rest[:stop.start()] if stop else rest[:120]
        return href, inner
    return None


def parse_rows(page_html: str, session_kind: str, session: str, table_url: str) -> tuple[list[dict], list[dict]]:
    tables = re.findall(r"(?is)<table\b.*?</table>", page_html)
    body = "\n".join(tables) if tables else page_html
    kept: list[dict] = []
    gaps: list[dict] = []
    for chunk in re.split(r"(?i)<tr\b", body):
        chosen = resolution_link(chunk)
        if not chosen:
            continue
        href, inner = chosen
        symbol = canonical_symbol(href) or canonical_symbol(inner)
        if not symbol:
            continue
        display = cell_text(inner).replace("\n", " ").strip() or symbol
        display = re.sub(r"\s+", " ", display)
        tds = re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", chunk)
        texts = [cell_text(td) for td in tds]
        date_cell = ""
        for text in texts:
            if DATE_RE.search(text):
                date_cell = text
                break
        iso, why, date_raw = parse_date(date_cell)
        title = ""
        if texts:
            last = re.sub(r"\s+", " ", texts[-1].replace("\n", " ")).strip()
            if last and not re.match(r"(?i)^A/RES/", last) and last != date_cell.replace("\n", " "):
                title = last
        title = title.rstrip(".").strip()
        lines = vote_lines(date_cell, date_raw) if date_raw else []
        vote, vote_raw = vote_zh(lines)
        row = {
            "session_kind": session_kind,
            "session": session,
            "symbol": symbol,
            "display": display if display.upper().startswith("A/RES/") else symbol,
            "date": iso or "",
            "date_raw": date_raw,
            "title": title,
            "vote_raw": vote_raw,
            "vote_zh": vote if iso else vote,
            "meeting": meeting_of(date_cell),
            "doc_url": absolute_doc(href),
            "library_url": "",
            "library_kind": "",
            "table_url": table_url,
        }
        if not iso:
            row["gap"] = why or "通过日期无记录"
            gaps.append({
                "symbol": display,
                "session_kind": session_kind,
                "session": session,
                "reason": row["gap"],
                "date_raw": date_raw,
                "title": title,
                "doc_url": row["doc_url"],
                "table_url": table_url,
            })
            continue
        if not title:
            row["title"] = ""
            row["vote_zh"] = vote
            gaps.append({
                "symbol": display,
                "session_kind": session_kind,
                "session": session,
                "reason": "标题无记录",
                "date": iso,
                "doc_url": row["doc_url"],
                "table_url": table_url,
            })
        kept.append(row)
    return kept, gaps


def iframe_url(page_html: str) -> str:
    match = re.search(r'src="([^"]*render_meeting_ga/[^"]+)"', page_html)
    if not match:
        return ""
    src = match.group(1)
    if src.startswith("//"):
        return "https:" + src
    return src


def load_page(kind: str, session: str, url: str) -> tuple[str, str, str, str]:
    page = fetch(url)
    frame = iframe_url(page)
    if frame and page.lower().count("undocs.org/a/res") + page.lower().count("docs.un.org/a/res") < 3:
        return kind, session, fetch(frame), url
    return kind, session, page, url


def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for row in rows:
        key = (
            row["display"], row["date"], row["title"], row["vote_raw"], row["doc_url"],
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    out.sort(key=lambda r: (r["date"], r["session_kind"], r["session"], r["symbol"], r["display"]))
    return out


def library_search(symbol: str) -> str:
    query = urllib.parse.quote(f'"{symbol}"')
    return f"https://digitallibrary.un.org/search?ln=en&p={query}"


def marc_records(xml: str) -> list[tuple[str, set[str], int]]:
    found = []
    for rec in re.findall(r"<record>(.*?)</record>", xml, re.S):
        rid = re.search(r'<controlfield tag="001">(\d+)</controlfield>', rec)
        if not rid:
            continue
        symbols = set()
        for field in re.findall(r'<datafield tag="191".*?</datafield>', rec, re.S):
            for sub in re.findall(r'<subfield code="a">(.*?)</subfield>', field, re.S):
                symbols.add(re.sub(r"\s+", "", sub))
        score = 0
        if re.search(r'<datafield tag="992".*?\d{4}-\d{2}-\d{2}', rec, re.S):
            score += 2
        if "Adopted at" in rec:
            score += 1
        found.append((rid.group(1), symbols, score))
    return found


def enrich_library(rows: list[dict]) -> dict:
    wanted = sorted({r["symbol"] for r in rows if r.get("symbol")})
    best: dict[str, tuple[int, str]] = {}
    batches = [wanted[i:i + 6] for i in range(0, len(wanted), 6)]
    stats = {"batches": len(batches), "errors": 0, "matched": 0}

    def one(batch: list[str]) -> list[tuple[str, set[str], int]]:
        query = " OR ".join(f'"{symbol}"' for symbol in batch)
        url = "https://digitallibrary.un.org/search?" + urllib.parse.urlencode({
            "ln": "en", "p": query, "of": "xm", "rg": "40",
        })
        return marc_records(fetch(url, timeout=90))

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(one, batch): batch for batch in batches}
        done = 0
        for fut in as_completed(futures):
            done += 1
            batch = futures[fut]
            try:
                recs = fut.result()
            except Exception as exc:
                stats["errors"] += 1
                print("library batch failed", batch[0], exc)
                continue
            for rid, symbols, score in recs:
                for symbol in symbols:
                    if symbol not in best or score > best[symbol][0]:
                        best[symbol] = (score, rid)
            if done % 40 == 0:
                print(f"library {done}/{len(batches)} matched {len(best)}")
    for row in rows:
        hit = best.get(row["symbol"])
        if hit:
            row["library_url"] = f"https://digitallibrary.un.org/record/{hit[1]}"
            row["library_kind"] = "record"
            stats["matched"] += 1
        else:
            row["library_url"] = library_search(row["symbol"])
            row["library_kind"] = "search"
    stats["symbols"] = len(wanted)
    stats["record_symbols"] = sum(1 for row in rows if row["library_kind"] == "record")
    return stats


ROMAN = {
    "I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6",
    "VII": "7", "VIII": "8", "IX": "9", "X": "10", "XI": "11", "XII": "12",
}


def session_number(kind: str, symbol: str, session: str) -> str:
    text = symbol or ""
    if kind == "emergency":
        match = re.search(r"ES-(\d+)", text)
        if match:
            return match.group(1)
        match = re.search(r"ES-([IVX]+)", text)
        if match:
            return ROMAN.get(match.group(1), "")
        return ""
    if kind == "special":
        match = re.search(r"S-(\d+)", text)
        if match:
            return match.group(1)
        match = re.search(r"S-([IVX]+)", text)
        if match:
            return ROMAN.get(match.group(1), "")
        return ""
    return session


def norm_symbol(text: str) -> str:
    return re.sub(r"\s+", "", text or "").upper()


def main() -> None:
    jobs = [("regular", str(n), f"https://research.un.org/en/docs/ga/quick/regular/{n}") for n in range(1, 82)]
    jobs.append(("emergency", "", "https://research.un.org/en/docs/ga/quick/emergency"))
    jobs.append(("special", "", "https://research.un.org/en/docs/ga/quick/special"))
    pages = []
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(load_page, kind, session, url): (kind, session, url) for kind, session, url in jobs}
        for fut in as_completed(futures):
            kind, session, url = futures[fut]
            try:
                pages.append(fut.result())
            except Exception as exc:
                failures.append({"session_kind": kind, "session": session, "url": url, "reason": str(exc)})
                print("page failed", kind, session, exc)
    print("pages", len(pages), "failures", len(failures))
    rows: list[dict] = []
    gaps: list[dict] = []
    page_counts: dict[tuple[str, str], int] = {}
    for kind, session, page_html, table_url in pages:
        got, missed = parse_rows(page_html, kind, session, table_url)
        rows.extend(got)
        gaps.extend(missed)
        page_counts[(kind, session)] = len(got)
        print(f"parsed {kind} {session or '-'} rows {len(got)} undated {len(missed)}")
    rows = dedupe(rows)
    dated_symbols = {norm_symbol(row["symbol"]) for row in rows}
    dated_symbols.update(norm_symbol(row["display"]) for row in rows)
    filtered_gaps = []
    for gap in gaps:
        # 表里指向已有决议、本身没有标题也没有日期的，是互见，不另算缺口。
        if gap.get("reason") == "通过日期无记录" and not (gap.get("title") or "").strip():
            if norm_symbol(gap.get("symbol") or "") in dated_symbols:
                continue
            if any(norm_symbol(gap.get("symbol") or "").startswith(sym) and sym.startswith("A/RES/377") for sym in dated_symbols):
                continue
        filtered_gaps.append(gap)
    gaps = filtered_gaps
    for row in rows:
        numbered = session_number(row["session_kind"], row["symbol"], row["session"])
        if row["session_kind"] != "regular":
            row["session"] = numbered
    print("dated rows", len(rows), "gap rows", len(gaps))
    for row in rows:
        row["library_url"] = library_search(row["symbol"])
        row["library_kind"] = "search"
    lib_stats = enrich_library(rows)
    print("library", lib_stats)

    by_session: dict[str, dict[str, int]] = {"regular": {}, "emergency": {}, "special": {}}
    for row in rows:
        bucket = by_session.setdefault(row["session_kind"], {})
        key = row["session"] or "?"
        bucket[key] = bucket.get(key, 0) + 1
    missing_regular = [str(n) for n in range(1, 82) if page_counts.get(("regular", str(n)), 0) == 0]
    coverage_gaps = []
    for item in failures:
        coverage_gaps.append({**item, "reason": "决议表页面没有取到：" + item["reason"]})
    for n in missing_regular:
        if any(g.get("session") == n and g.get("session_kind") == "regular" for g in coverage_gaps):
            continue
        coverage_gaps.append({
            "session_kind": "regular",
            "session": n,
            "reason": "这一届的决议表没有解析到带通过日期的决议",
        })

    def hole(kind: str) -> list[str]:
        nums = []
        for key in by_session.get(kind, {}):
            if key.isdigit():
                nums.append(int(key))
        if not nums:
            return []
        present = set(nums)
        return [str(n) for n in range(1, max(present) + 1) if n not in present]

    for kind, label in (("emergency", "紧急特别届"), ("special", "特别届")):
        for n in hole(kind):
            coverage_gaps.append({
                "session_kind": kind,
                "session": n,
                "reason": f"{label}决议表从第1届到已出现的最大届次之间，没有这一届的决议行",
            })

    vote_none = sum(1 for row in rows if row.get("vote_zh") == "无")
    search_only = sum(1 for row in rows if row.get("library_kind") == "search")
    payload = {
        "note": (
            "联合国大会决议，按达格·哈马舍尔德图书馆决议表收录。"
            "常规届1至81、紧急特别届、特别届各用该馆对应的表。"
            "文号、标题、表决和通过日期只取表上写明的内容；表决空着写无。"
            "三位数表决按该表记法转写为赞成-反对-弃权，并保留原串。"
            "日期是区间或不止一个时不写成单日，放在 gaps。"
            "决议文本链到表上给出的联合国正式文件系统（undocs.org 或 docs.un.org）。"
            "数字图书馆对上文号记录的写记录链接，没对上的只给按文号检索的链接。"
            "不补表上没有的决议。"
        ),
        "stats": {
            "dated": len(rows),
            "vote_none": vote_none,
            "library_record": len(rows) - search_only,
            "library_search_only": search_only,
            "library_errors": lib_stats.get("errors", 0),
            "undated_or_range": len(gaps),
            "regular_sessions_with_rows": len(by_session.get("regular", {})),
            "emergency_sessions_with_rows": len(by_session.get("emergency", {})),
            "special_sessions_with_rows": len(by_session.get("special", {})),
        },
        "by_session": {
            kind: dict(sorted(bucket.items(), key=lambda kv: (len(kv[0]), kv[0])))
            for kind, bucket in by_session.items()
        },
        "gaps": coverage_gaps + gaps,
        "resolutions": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)
    interesting = ("181(II)", "377(V)", "1514(XV)", "2758(XXVI)", "3379(XXX)", "46/86", "68/262", "ES-11/4", "ES-11/1")
    for row in rows:
        if any(token in row["symbol"] or token in row["display"] for token in interesting):
            if "377" in row["symbol"] or any(token in row["symbol"] for token in interesting if token != "377(V)"):
                print(
                    row["date"], row["display"], row["vote_zh"], row["title"][:80],
                    row["library_kind"], row["doc_url"],
                )


if __name__ == "__main__":
    main()
