"""把官方列表收成机构树上的决议和判例。

安理会：联合国数字图书馆按年的 S/RES 记录（通过日在 992 字段），
议题优先用安全理事会决议索引页。2014 年起索引页自带日期。
国际法院和常设国际法院：icj-cij.org 的判决与咨询意见，不含命令。
大会只留五条样例。

下载放在 /tmp，本脚本只写 data/curated/diplomacy_acts.json。
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "curated" / "diplomacy_acts.json"
INDEX = Path("/home/ubuntu/.cursor/projects/agent-repos-world-history-atlas/agent-tools/d78e45ae-7762-41e8-ab63-661663ccde13.txt")
SC_DIR = Path("/tmp/scxml")
ICJ = Path("/tmp/icj")

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "jully": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12, "décembre": 12, "decembre": 12,
}


def iso_from_words(text: str) -> str | None:
    m = re.search(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})", text)
    if not m:
        return None
    word = "".join(ch for ch in unicodedata.normalize("NFKD", m.group(2).lower()) if ch.isascii())
    mon = MONTHS.get(word) or MONTHS.get(m.group(2).lower())
    if not mon:
        return None
    return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"


def sub(field: str, code: str) -> str:
    m = re.search(rf'<subfield code="{code}">(.*?)</subfield>', field, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def fields(record: str, tag: str) -> list[str]:
    return re.findall(rf'<datafield tag="{tag}".*?</datafield>', record, re.S)


def parse_index() -> dict[int, dict]:
    out = {}
    if not INDEX.exists():
        return out
    date_re = re.compile(r"S/RES/(\d+)\s*\((\d{4})\)\s*\|\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*\|\s*(.*?)\s*\|")
    plain_re = re.compile(r"S/RES/(\d+)\s*\((\d{4})\)\s*\|\s*(.*?)\s*\|")
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        m = date_re.search(line)
        if m:
            num = int(m.group(1))
            out[num] = {"year": int(m.group(2)), "date": iso_from_words(m.group(3)), "topic": m.group(4).strip()}
            continue
        m = plain_re.search(line)
        if m and not re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", line):
            num = int(m.group(1))
            out[num] = {"year": int(m.group(2)), "date": None, "topic": m.group(3).strip()}
    return out


def parse_sc_xml(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    found = {}
    for rec in re.findall(r"<record>(.*?)</record>", text, re.S):
        sym = ""
        for fld in fields(rec, "191"):
            sym = sub(fld, "a") or sym
        m = re.fullmatch(r"S/RES/(\d+)\s*\((\d{4})\)", sym.strip())
        if not m:
            continue
        num = int(m.group(1))
        date = ""
        for fld in fields(rec, "992"):
            val = sub(fld, "a")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
                date = val
                break
        if not date:
            for fld in fields(rec, "245"):
                date = iso_from_words(sub(fld, "c")) or ""
                if date:
                    break
        topic = ""
        for fld in fields(rec, "991"):
            topic = sub(fld, "c") or topic
        title = ""
        for fld in fields(rec, "239"):
            title = sub(fld, "a") or title
        recid = re.search(r'<controlfield tag="001">(\d+)</controlfield>', rec)
        url = f"https://digitallibrary.un.org/record/{recid.group(1)}" if recid else ""
        row = {"year": int(m.group(2)), "date": date or None, "topic": topic or title, "url": url}
        prev = found.get(num)
        if prev is None or (not prev.get("date") and row["date"]):
            found[num] = row
    return found


def sc_acts(index: dict[int, dict]) -> tuple[list[dict], dict]:
    library = {}
    for year in range(1946, 2027):
        for name in (f"{year}.xml", f"{year}b.xml"):
            library.update(parse_sc_xml(SC_DIR / name))
    nums = sorted(set(index) | set(library))
    acts = []
    stats = {"index": len(index), "library": len(library), "no_date": 0, "date_mismatch": 0}
    for num in nums:
        ind = index.get(num) or {}
        lib = library.get(num) or {}
        # 索引页写了日期就用索引页。两边差一天的有几条，不改成馆藏日期。
        date = ind.get("date") or lib.get("date")
        if ind.get("date") and lib.get("date") and ind["date"] != lib["date"]:
            stats["date_mismatch"] += 1
        topic = ind.get("topic") or lib.get("topic") or ""
        if not date:
            stats["no_date"] += 1
            continue
        year = ind.get("year") or lib.get("year")
        url = lib.get("url") or "https://main.un.org/securitycouncil/en/content/resolutions-0"
        acts.append({
            "date": date,
            "zh": f"第{num}（{year}）号决议：{topic}" if topic else f"第{num}（{year}）号决议",
            "url": url,
            "label": "联合国数字图书馆的决议记录；议题来自安全理事会决议索引",
        })
    acts.sort(key=lambda a: (a["date"], a["zh"]))
    stats["kept"] = len(acts)
    return acts, stats


def html_text(fragment: str) -> str:
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", fragment).replace("&quot;", '"').replace("&#039;", "'").strip()


def parse_icj(path: Path, kind: str) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    pat = re.compile(
        r">\s*((?:Judgment|Advisory [Oo]pinion) of [^<]+)</a>(.{0,1200}?)"
        r'href="(/case/\d+)"[^>]*>(.*?)</a>',
        re.S,
    )
    acts = []
    for heading_raw, tail, href, case_raw in pat.findall(html):
        heading = html_text(heading_raw)
        date = iso_from_words(heading)
        if not date:
            continue
        case = html_text(case_raw)
        sub_m = re.search(r'views-field-field-icj-document-subtitle.*?<div class="field-content">(.*?)</div>', tail, re.S)
        sub = html_text(sub_m.group(1)) if sub_m else ""
        kind_zh = "判决" if heading.lower().startswith("judgment") else "咨询意见"
        zh = f"{case}：{heading}" if case else heading
        if sub:
            zh += f"（{sub}）"
        acts.append({
            "date": date,
            "zh": zh,
            "url": "https://www.icj-cij.org" + href,
            "label": "国际法院判决与咨询意见列表",
            "kind": kind_zh,
        })
    return acts


def parse_pcij(path: Path) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    # 按出现顺序走标题和文件链接。判决行有时写在案名之前。
    tokens = re.findall(
        r"<h3>(.*?)</h3>|<h4[^>]*>(.*?)</h4>|<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>",
        html,
        re.S,
    )
    series = ""
    title = ""
    pending: list[dict] = []
    acts = []

    def flush_title():
        nonlocal pending
        for row in pending:
            phrase = row.pop("_h", "")
            if title:
                row["zh"] = f"{series} {title}：{phrase}" if series else f"{title}：{phrase}"
        acts.extend(pending)
        pending = []

    for h3, h4, href, link in tokens:
        if h3:
            flush_title()
            series = html_text(h3)
            title = ""
            continue
        if h4:
            title = html_text(h4)
            title = re.sub(rf"^{re.escape(series)}\s*", "", title).strip()
            flush_title()
            continue
        text = html_text(link)
        if not re.match(r"(Judgment of |Advisory Opinion of )", text, re.I):
            continue
        date = iso_from_words(text)
        if not date:
            continue
        url = href if href.startswith("http") else "https://www.icj-cij.org" + href
        row = {
            "date": date,
            "zh": f"{series}：{text}" if series else text,
            "url": url,
            "label": "常设国际法院系列出版物",
            "kind": "判决" if text.lower().startswith("judgment") else "咨询意见",
            "_h": text,
        }
        if title:
            row.pop("_h", None)
            row["zh"] = f"{series} {title}：{text}" if series else f"{title}：{text}"
            acts.append(row)
        else:
            pending.append(row)
    flush_title()
    return acts


def main():
    index = parse_index()
    sc, sc_stats = sc_acts(index)
    icj = parse_icj(ICJ / "j.html", "icj") + parse_icj(ICJ / "adv.html", "icj")
    # judgments file may have been saved beside the downloader
    if not (ICJ / "j.html").exists():
        alt = Path("/tmp/icj-j.html")
        if alt.exists():
            icj = parse_icj(alt, "icj") + parse_icj(ICJ / "adv.html", "icj")
    pcij = []
    for name in ("a.html", "b.html", "ab.html"):
        pcij.extend(parse_pcij(ICJ / name))
    # 同一天、同一链接只留一条。
    def dedupe(rows):
        seen = set()
        out = []
        for row in rows:
            key = (row["date"], row["url"], row["zh"])
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        out.sort(key=lambda a: (a["date"], a["zh"]))
        return out

    payload = {
        "ga_note": "大会决议仅收录部分",
        "sources": [
            {"label": "安全理事会决议索引", "url": "https://main.un.org/securitycouncil/en/content/resolutions-0"},
            {"label": "联合国数字图书馆", "url": "https://digitallibrary.un.org/"},
            {"label": "国际法院判决、咨询意见和命令", "url": "https://www.icj-cij.org/decisions"},
            {"label": "常设国际法院", "url": "https://www.icj-cij.org/pcij"},
        ],
        "organs": {
            "sc": dedupe(sc),
            "icj": dedupe(icj),
            "pcij": dedupe(pcij),
            "ga": [
                {
                    "date": "1947-11-29",
                    "zh": "第181（II）号决议：Future government of Palestine",
                    "url": "https://digitallibrary.un.org/record/210008",
                    "label": "大会决议样例。通过日写在记录里：1947年11月29日第128次全体会议。大会决议仅收录部分",
                },
                {
                    "date": "1950-11-03",
                    "zh": "第377（V）号决议：Uniting for peace",
                    "url": "https://digitallibrary.un.org/record/666468",
                    "label": "大会决议样例。大会决议仅收录部分",
                },
                {
                    "date": "1971-10-25",
                    "zh": "第2758（XXVI）号决议：Restoration of the lawful rights of the People's Republic of China in the United Nations",
                    "url": "https://digitallibrary.un.org/record/192054",
                    "label": "大会决议样例。大会决议仅收录部分",
                },
                {
                    "date": "2014-03-27",
                    "zh": "第68/262号决议：Territorial integrity of Ukraine",
                    "url": "https://digitallibrary.un.org/record/767883",
                    "label": "大会决议样例。大会决议仅收录部分",
                },
                {
                    "date": "2022-10-12",
                    "zh": "第ES-11/4号决议：Territorial integrity of Ukraine: defending the principles of the Charter of the United Nations",
                    "url": "https://digitallibrary.un.org/record/3990673",
                    "label": "大会决议样例。大会决议仅收录部分",
                },
            ],
        },
    }
    # 大会这五条的中文是议题的短称，日期和文号要在测试里对上官方记录。
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("sc", sc_stats, "icj", len(payload["organs"]["icj"]), "pcij", len(payload["organs"]["pcij"]))
    print("bytes", OUT.stat().st_size)
    r83 = [a for a in payload["organs"]["sc"] if a["date"] == "1950-06-27" and "83" in a["zh"]]
    print("r83", r83[:2])
    nic = [a for a in payload["organs"]["icj"] if a["date"] == "1986-06-27"]
    print("nic", nic[:3])
    lotus = [a for a in payload["organs"]["pcij"] if a["date"] == "1927-09-07"]
    print("lotus", lotus[:2])
    corfu = [a for a in payload["organs"]["icj"] if a["date"] == "1949-04-09"]
    print("corfu", corfu[:2])


if __name__ == "__main__":
    main()
