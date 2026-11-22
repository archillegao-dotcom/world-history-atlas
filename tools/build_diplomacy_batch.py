"""补外交面板的四份成员名单：常设仲裁法院、万国邮政联盟、万国电报联盟、欧洲协调。

仲裁法院的生效日来自荷兰保存机关两份缔约方表，并与法院缔约方页对过。
邮政联盟的加入日来自各会员法律地位页上的 “UPU member since”。
不写大会决议。
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "curated_src"
CUR = ROOT / "data" / "curated"

UPU_SKIP = {
    "aut", "bel", "che", "deu", "dnk", "egy", "esp", "gbr", "grc", "hun",
    "ita", "lux", "nld", "nor", "prt", "rou", "rus", "srb", "swe", "tur",
    "usa", "fra",
}


def read_tsv(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    out = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        out.append(dict(zip(header, cells)))
    return out


def iso(dmy: str) -> str:
    dmy = (dmy or "").strip()
    if not dmy:
        return ""
    d, m, y = dmy.split("-")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def prev_day(day: str) -> str:
    y, m, d = (int(x) for x in day.split("-"))
    return (date(y, m, d) - timedelta(days=1)).isoformat()


def norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    aliases = {
        "austria hungary": "austria hungary",
        "kingdom of sweden and norway": "sweden norway",
        "czechoslovakia 01 01 1993": "czechoslovakia",
        "haiti": "haiti",
        "turkiye": "turkiye",
        "turkey": "turkiye",
        "czechia": "czech republic",
        "czech republic": "czech republic",
        "laos": "laos",
        "lao peoples democratic republic": "laos",
        "democratic republic of the congo": "dr congo",
        "congo democratic republic of the": "dr congo",
        "netherlands": "netherlands",
        "netherlands the kingdom of the": "netherlands",
        "united kingdom": "united kingdom",
        "united kingdom of great britain and northern ireland": "united kingdom",
        "korea republic of": "korea republic",
        "republic of korea the": "korea republic",
        "bahamas": "bahamas",
        "bahamas the": "bahamas",
        "the bahamas": "bahamas",
        "viet nam": "vietnam",
        "vietnam": "vietnam",
        "sao tome e principe": "sao tome",
        "sao tome and principe democratic republic of": "sao tome",
        "china peoples republic of": "china",
        "china": "china",
        "slovak republic": "slovakia",
        "slovakia": "slovakia",
        "eswatini": "eswatini",
        "swaziland": "eswatini",
        "russian federation": "russian federation",
        "bolivia": "bolivia",
        "plurinational state of bolivia": "bolivia",
    }
    return aliases.get(text, text)


def kind_of(rat: str) -> str:
    m = re.search(r"\(([A-Za-z]+)\)", rat or "")
    if not m:
        return ""
    word = {"R": "批准", "A": "加入", "Su": "继承", "S": "签署"}.get(m.group(1), m.group(1))
    return word


def build_pca() -> tuple[list[dict], dict]:
    rows: dict[str, dict] = {}

    def slot(name: str) -> dict:
        key = norm(name)
        row = rows.get(key)
        if row is None:
            row = {"key": key, "name": name, "c": {}}
            rows[key] = row
        return row

    for conv, path in (("1899", SRC / "pca_1899.tsv"), ("1907", SRC / "pca_1907.tsv")):
        for rec in read_tsv(path):
            row = slot(rec["name"])
            # 保存机关的历史名称优先于后来公约里的现用名称。
            if conv == "1899" or row["name"] == rec["name"]:
                if conv == "1899":
                    row["name"] = rec["name"]
            row["c"][conv] = rec
    page = {}
    for rec in read_tsv(SRC / "pca_page.tsv"):
        page[norm(rec["name"])] = rec

    members = []
    only_page = []
    only_dep = []
    signed_only = []
    conflicts = []
    for key, rec in page.items():
        if key not in rows:
            only_page.append(rec["name"])
    for key, row in rows.items():
        if key not in page and key not in {"austria hungary", "sweden norway", "czechoslovakia"}:
            only_dep.append(row["name"])
        for conv, rec in row["c"].items():
            if rec.get("signature") and not rec.get("eif"):
                signed_only.append(f"{row['name']}（{conv}）")

    for key, row in sorted(rows.items(), key=lambda kv: kv[1]["name"]):
        eifs = {}
        for conv, rec in row["c"].items():
            day = iso(rec.get("eif", ""))
            if day:
                eifs[conv] = day
        if not eifs:
            continue
        start_conv = min(eifs, key=lambda c: eifs[c])
        start = eifs[start_conv]
        pca = page.get(key)
        uncertain = None
        notes = []
        if pca:
            pca_day = iso(pca.get(start_conv, ""))
            # 法院页把瑞典、挪威的 1899 年栏写成联合的生效日，不拿来否定单独一行。
            union_shadow = key in {"sweden", "norway"} and start_conv == "1899" and pca_day == "1900-09-04" and start == "1905-06-17"
            if union_shadow:
                notes.append("法院页把这一国的1899年栏写成1900-09-04，与瑞典和挪威联合的生效日相同。单独这一行用保存机关的1905-06-17。")
            elif pca_day and pca_day != start:
                later = max(start, pca_day)
                earlier = min(start, pca_day)
                uncertain = (earlier, prev_day(later))
                start = later
                conflicts.append(f"{row['name']} {start_conv} {earlier}/{later}")
                notes.append(f"保存机关和法院页的{start_conv}年公约生效日不一致，加入日待考，不择一。从较晚的{later}起写成成员国。")
            elif not pca_day:
                notes.append(f"法院页没有{start_conv}年公约这一栏。生效日用保存机关。")
        else:
            notes.append("法院现行缔约方页没有这个名称。")

        if key == "montenegro":
            uncertain = ("2006-06-03", "2007-02-28")
            start = "2007-03-01"
            notes.append("保存机关声明写自2006年6月3日继承，生效栏是2007年3月1日，与法院页一致。两说不择一。")
        if key == "russian federation":
            notes.append("1955年3月7日的声明是苏联承认俄国已经批准的公约，不是生效栏里的另一个日期。表上名称是 Russian Federation。不另开苏联一行，也不改写成1899年的国名。")
        if key == "china":
            notes.append("法院页写 China, People’s Republic of，保存机关写 China。不把中华人民共和国写成1904年的成员名称。香港、澳门的适用延伸不单列。")
        if key == "united kingdom":
            notes.append("1907年公约的生效日不是会籍起算日。属地延伸不单列成员。")

        how = ""
        until = ""
        if key == "austria hungary":
            until = "1918-11-12"
            how = "gap"
            notes.append("终止栏是空的。法院现行缔约方页没有奥匈。奥地利从1918-11-12另有生效行。从那天起这一行标席位待考，不是退出文书。")
        elif key == "sweden norway":
            until = "1905-06-17"
            how = "gap"
            notes.append("终止栏是空的。瑞典和挪威从1905-06-17各有一行。从那天起这一行标席位待考，不是退出文书。")
        elif key == "czechoslovakia":
            until = "1993-01-01"
            how = "dissolved"
            notes.append("行名写 Czechoslovakia (<01-01-1993)。终止栏是空的。从1993-01-01起这一行不再算仍在的缔约方，会籍不自动传给后继。")
        if key == "czech republic":
            notes.append("前身行写到1993-01-01为止。这一行的生效日另计，中间不补成自动继承。")
        if key == "slovakia":
            notes.append("前身行写到1993-01-01为止。这一行的生效日另计，中间不补成自动继承。")

        bits = []
        for conv in ("1899", "1907"):
            rec = row["c"].get(conv)
            if not rec:
                bits.append(f"{conv}年公约：保存机关表无这一行")
                continue
            sig = iso(rec.get("signature", "")) or "无"
            rat = kind_of(rec.get("ratification", "")) or "无"
            eif = iso(rec.get("eif", "")) or "无"
            bits.append(f"{conv}年公约：签署{sig}，{rat}，生效{eif}")
        bits.append("退出栏空，终止栏空。暂停无记录。")
        if pca:
            bits.append(
                "法院页1899 "
                + (iso(pca.get("1899", "")) or "无")
                + "，1907 "
                + (iso(pca.get("1907", "")) or "无")
                + "。"
            )
        bits.extend(notes)
        member = {
            "name": row["name"] + "（表上名称）",
            "from": start,
            "track": "dated",
            "hide_before": True,
            "role": "成员国",
            "note": "".join(bits),
        }
        if uncertain:
            member["join_uncertain_from"] = uncertain[0]
            member["join_uncertain_until"] = uncertain[1]
        if until:
            member["until"] = until
            member["how"] = how
        members.append(member)

    stats = {
        "members": len(members),
        "only_page": only_page,
        "only_dep": only_dep,
        "signed_only": signed_only,
        "conflicts": conflicts,
    }
    return members, stats


def build_upu(founding: list[dict]) -> tuple[list[dict], dict]:
    founding = [m for m in founding if "页上现称" not in (m.get("name") or "")]
    extra = []
    blank = []
    for rec in read_tsv(SRC / "upu_member_since.tsv"):
        if not rec["member_since"]:
            blank.append(rec["name"] or rec["code"])
            continue
        if rec["code"] in UPU_SKIP:
            continue
        if rec["member_since"] <= "1875-07-01":
            continue
        url = (
            "https://www.upu.int/UPU/media/upu/files/aboutUpu/acts/"
            f"10-memberCountriesLegalSituation/{rec['code']}En.pdf"
        )
        note = (
            f"万国邮政联盟法律地位页写 UPU member since {rec['member_since']}。"
            "页上用现在的国名，没有写当时政权，也没有写退出、暂停、继承。不配政权编号。"
            f" {url}"
        )
        if rec["code"] == "ssd":
            note += " 万国邮政联盟2011年10月6日的新闻稿写成员资格于2011年10月4日生效，与这一页相同。"
        extra.append({
            "name": rec["name"] + "（页上现称）",
            "from": rec["member_since"],
            "track": "dated",
            "hide_before": True,
            "role": "成员国",
            "note": note,
        })
    # 不覆盖 1874 年缔约方。
    names = {m.get("name") for m in founding}
    extra = [m for m in extra if m["name"] not in names]
    return founding + extra, {"added": len(extra), "blank": blank, "kept_founding": len(founding)}


def main():
    dip_path = CUR / "diplomacy.json"
    data = json.loads(dip_path.read_text(encoding="utf-8"))
    by_id = {org["id"]: org for org in data["orgs"]}

    members, stats = build_pca()
    (CUR / "pca_members.json").write_text(
        json.dumps({"members": members}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pca = by_id["pca"]
    pca["members"] = []
    pca["members_file"] = "pca_members.json"
    pca["incomplete"] = True
    pca["summary"] = (
        "1899年7月29日《和平解决国际争端公约》在海牙签署，第20条起规定设立常设仲裁法院。"
        "保存机关是荷兰政府。公约对已经交存批准书的国家从1900年9月4日起生效。"
        "缔约方按保存机关表的生效日写入。只有签署、生效栏空白的，不写成缔约方。"
        "法院网页和保存机关的生效日不一致时标加入日待考，不择一。"
        "读到的退出栏和终止栏都是空的，不编退出。表上没有暂停栏，标无。"
        "名称用表上的写法，不改成当时的国名，也不配政权编号。"
    )
    pca["list_note"] = (
        f"这一批写入{stats['members']}行，仍标名单不完整。"
        "奥匈、瑞典和挪威联合的终止栏是空的，后继行出现后标席位待考，不是退出文书。"
        "捷克斯洛伐克的行名写到1993-01-01为止，会籍不自动传给后继。"
        "已签署而生效栏空白、因而不写入的有："
        + "、".join(stats["signed_only"])
        + "。"
        "法院页有、保存机关这两张表没有对上的，不写入："
        + ("、".join(stats["only_page"]) if stats["only_page"] else "无")
        + "。"
        "生效日两说、标了加入日待考的有："
        + ("、".join(stats["conflicts"]) if stats["conflicts"] else "无")
        + "。属地延伸不单列。暂停无记录。"
    )
    pca["sources"] = [
        {"label": "1899年公约缔约方（荷兰保存机关）", "url": "https://verdragenbank.overheid.nl/en/Treaty/Details/002330_p.html"},
        {"label": "1907年公约缔约方（荷兰保存机关）", "url": "https://verdragenbank.overheid.nl/en/Treaty/Details/003316_p.html"},
        {"label": "常设仲裁法院缔约方页", "url": "https://pca-cpa.org/en/about/introduction/contracting-parties/"},
        {"label": "1899年公约，美国国务院历史文件", "url": "https://history.state.gov/historicaldocuments/frus1902app2/d20"},
    ]

    upu = by_id["upu"]
    merged, ustats = build_upu(upu.get("members") or [])
    upu["members"] = merged
    upu["incomplete"] = True
    upu["summary"] = (
        "1874年10月9日在伯尔尼签署《邮政总联盟条约》，1875年7月1日生效。"
        "1878年6月1日的公约取代1874年文本，名称改为万国邮政联盟。组织没有另起一个。"
        "1875年7月1日及以前的法律地位页用的是现在的国名，不另开一行，1874年的缔约方仍写签署方、后来的会籍未核。"
        "比这晚的 member since 另列，名称仍是页上的现称，不改写成当时政权，不配政权编号。"
        "这些页没有写退出、暂停、继承，标无。"
    )
    upu["list_note"] = (
        "1874年条约标题上的缔约方仍在。奥匈帝国不拆。"
        f"另按法律地位页写入{ustats['added']}行，member since 都晚于1875年7月1日。"
        "法国页上写1876年1月1日，与缔约日不同，不另开一行，也不改缔约方原行。"
        "没有 member since、因而不写入的有："
        + "、".join(ustats["blank"])
        + "。退出、暂停、继承：这些页没有写，标无。名单仍不完整。"
    )
    sources = list(upu.get("sources") or [])
    extra_src = [
        {"label": "万国邮政联盟会员法律地位页（按国家）", "url": "https://www.upu.int/UPU/media/upu/files/aboutUpu/acts/10-memberCountriesLegalSituation/ssdEn.pdf"},
        {"label": "南苏丹于2011年10月4日成为会员", "url": "https://www.upu.int/en/news/2011/10/south-sudan-becomes-192nd-member-country"},
    ]
    have = {s["url"] for s in sources}
    for src in extra_src:
        if src["url"] not in have:
            sources.append(src)
    upu["sources"] = sources

    itu = by_id["itu"]
    if not any(m.get("from") == "2011-10-03" and "南苏丹" in (m.get("name") or "") for m in itu.get("members") or []):
        itu.setdefault("members", []).append({
            "name": "南苏丹",
            "from": "2011-10-03",
            "track": "dated",
            "hide_before": True,
            "role": "成员国",
            "note": "国际电信联盟全权代表大会页面写：最近加入的会员是南苏丹，2011年10月3日加入。没有另写退出或暂停。",
        })
    itu["incomplete"] = True
    itu["list_note"] = (
        "名单不完整。20个签署方仍是签署方，后来的会籍未核。"
        "会员页没有逐国加入日。1992年组织法的批准、接受或加入日不是会籍开始日，不拿来补名单。"
        "南苏丹按全权代表大会页面写入2011年10月3日。"
        "其余加入、退出、暂停、继承：无记录。"
    )
    itu["summary"] = (
        "1865年5月17日，20个国家在巴黎签署国际电报公约，成立万国电报联盟。"
        "1932年马德里会议另订国际电信公约。那份公约哪一天生效，这一批没有打开批准记录，所以名称仍用万国电报联盟。"
        "南苏丹于2011年10月3日加入。除此之外，后来的加入、退出、暂停和继承没有逐条的官方日子，不编。"
    )
    itu_sources = list(itu.get("sources") or [])
    itu_url = "https://www.itu.int/web/pp-18/en/article/itus-evolving-membership"
    if itu_url not in {s["url"] for s in itu_sources}:
        itu_sources.append({"label": "国际电信联盟：南苏丹2011年10月3日加入", "url": itu_url})
    itu["sources"] = itu_sources

    concert = by_id["concert"]
    concert["list_note"] = (
        "名单不完整。下面只列同盟条款里的四个主导国，以及1818年加入会商的法国。"
        "维也纳会议还有许多别的与会国，没有写成会员。"
        "加入只多了法国这一条。退出、暂停、继承：无记录。"
        "不把1822年维罗纳会议之后英国不再参加对别国内部的干涉写成退出。"
    )

    dip_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("pca", stats["members"], "conflicts", stats["conflicts"])
    print("only_page", stats["only_page"])
    print("only_dep", stats["only_dep"])
    print("signed_only", stats["signed_only"])
    print("upu added", ustats)


if __name__ == "__main__":
    main()
