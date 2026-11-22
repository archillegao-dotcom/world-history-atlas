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
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text).strip()
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


def _dk(day: str) -> float:
    y, m, d = (int(x) for x in day.split("-"))
    return y + (m - 1) / 12 + d / 372


def _covers(rec: dict | None, day: str, start: bool) -> bool:
    if not rec or not rec.get("y"):
        return not start
    y, m, d = rec["y"], rec.get("m") or 0, rec.get("d") or 0
    p = rec.get("p") or 9
    yy, mm, dd = (int(x) for x in day.split("-"))
    if start:
        if p >= 11 and m and d:
            return (y, m, d) <= (yy, mm, dd)
        if p == 10 and m:
            return (y, m) < (yy, mm)
        return y < yy
    if p >= 11 and m and d:
        return (yy, mm, dd) < (y, m, d)
    if p == 10 and m:
        return (yy, mm) < (y, m)
    return yy < y


def _labels(state: dict) -> set[str]:
    raw = [state.get("en") or "", state.get("zh") or ""] + list(state.get("aliases") or [])
    return {norm(x) for x in raw if norm(x)}


def link_polities(members: list[dict], pred) -> dict:
    """只在加入日当天名称唯一、存续盖住这一天时挂编号。政权链当天只有一个非并立政权时，用那一行。"""
    import lzma
    states = json.loads(lzma.open(ROOT / "data" / "states.json.xz").read())
    chains = json.loads((CUR / "regime_chains.json").read_text(encoding="utf-8")).get("chains") or {}
    by_q = {}
    for cq, chain in chains.items():
        by_q.setdefault(cq, cq)
        for row in chain.get("rows") or []:
            if row.get("qid"):
                by_q.setdefault(row["qid"], cq)
    linked = skipped = 0
    for member in members:
        if not pred(member):
            continue
        official = member.get("name") or ""
        official = official.replace("（页上现称）", "").replace("（表上名称）", "")
        key = norm(official)
        day = member.get("from") or ""
        if not key or not day:
            continue
        hits = []
        for state in states:
            if key not in _labels(state):
                continue
            if _covers(state.get("from"), day, True) and _covers(state.get("to"), day, False):
                hits.append(state)
        qid = ""
        basis = ""
        if len(hits) == 1:
            state = hits[0]
            cq = by_q.get(state["id"])
            if cq:
                dk = _dk(day)
                now = []
                for row in chains[cq].get("rows") or []:
                    if row.get("parallel"):
                        continue
                    a = _dk(row["from"]) if row.get("from") else None
                    b = _dk(row["to"]) if row.get("to") else None
                    if (a is None or a <= dk) and (b is None or dk < b) and row.get("qid"):
                        now.append(row)
                if len(now) == 1:
                    qid = now[0]["qid"]
                    basis = f"加入日当天政权链只有{now[0].get('zh') or qid}。{now[0].get('src') or ''}"
            else:
                qid = state["id"]
                basis = f"加入日当天名称与这一行相同、而且存续盖住这一天的政权只有{state.get('zh') or state.get('en') or qid}。"
        if qid:
            member["qid"] = qid
            member["match"] = [qid]
            note = member.get("note") or ""
            tag = "编号："
            if tag not in note:
                member["note"] = note + tag + basis
            linked += 1
        else:
            member.pop("qid", None)
            member.pop("match", None)
            skipped += 1
    return {"linked": linked, "unlinked": skipped}


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


def _mem(name, start, note, role="成员国", **extra):
    row = {
        "name": name,
        "from": start,
        "track": "dated",
        "hide_before": True,
        "role": role,
        "note": note,
    }
    row.update(extra)
    return row


def _upsert(data, org, after_id):
    orgs = data["orgs"]
    for i, old in enumerate(orgs):
        if old["id"] == org["id"]:
            orgs[i] = org
            return
    idx = next(i for i, old in enumerate(orgs) if old["id"] == after_id)
    orgs.insert(idx + 1, org)


def early_orgs() -> list[tuple[dict, str]]:
    """只写入官网上有完整日子的成员。年而没有日的变化写在注里，不设停止日。"""
    ccnr_states = (
        "史页写1815年6月9日《维也纳会议最后议定书》附件16B设立委员会，总部美因茨，"
        "成员是沿岸的巴登、巴伐利亚、黑森、拿骚、普鲁士，以及法国和荷兰。"
        "1919年6月28日凡尔赛条约这一天起，史页写由德国取代各邦。"
    )
    ccnr = {
        "id": "ccnr",
        "zh": "莱茵河航运中央委员会",
        "en": "Central Commission for the Navigation of the Rhine",
        "type": "organization",
        "type_zh": "正式国际组织",
        "from": "1815-06-09",
        "until": None,
        "signed": None,
        "effective": "1815-06-09",
        "headquarters": [
            {"from": "1815-06-09", "until": "1919-06-28", "text": "美因茨。1860年迁到曼海姆，史页没有写日，不另设一行。"},
            {"from": "1919-06-28", "text": "斯特拉斯堡。史页写凡尔赛条约把总部改到这里。"},
        ],
        "summary": (
            "委员会史页写：1815年6月9日《维也纳会议最后议定书》附件16B设立中央委员会，总部在美因茨。"
            "1868年10月17日曼海姆文件改了航行规则，组织还是这一个。"
            "1871年《法兰克福条约》之后法国不再是会员，史页没有写日，不设停止日。"
            "1919年6月28日凡尔赛条约改组委员会，法国回到，瑞士、比利时、英国、意大利加入，德国取代各邦。"
            "德国和意大利退出的年份，史页写1936年，组织页写意大利是1935年，两说都没有日，不设停止日。"
            "1945年11月20日复会时的代表团是美国、比利时、英国、荷兰、法国、瑞士。美国1961年离开、英国1993年离开、德国1950年才回来，都只有年，不设停止日或恢复日。"
        ),
        "incomplete": True,
        "list_note": (
            "只写入史页给了完整日子的成员。没有日的退出、恢复和暂停不设日子，标无。"
            "各邦在1919年6月28日起由德国取代，这是史页把变化系在凡尔赛条约这一天，不是另一份退出文书。"
        ),
        "sources": [
            {"label": "莱茵河航运中央委员会史", "url": "https://www.ccr-zkr.org/en/history"},
            {"label": "委员会的成员说明", "url": "https://www.ccr-zkr.org/11030200-en.html"},
        ],
        "members": [
            _mem("Baden", "1815-06-09", ccnr_states, until="1919-06-28", how="replaced"),
            _mem("Bavaria", "1815-06-09", ccnr_states, until="1919-06-28", how="replaced"),
            _mem("Hesse（史页未写是哪一个）", "1815-06-09", ccnr_states + "史页只写 Hesse，没有写是哪一个黑森，不挂编号。", until="1919-06-28", how="replaced"),
            _mem("Nassau", "1815-06-09", ccnr_states, until="1919-06-28", how="replaced"),
            _mem("Prussia（史页未区分王国和总条目）", "1815-06-09", ccnr_states + "图里同时有普鲁士和普鲁士王国，史页只写 Prussia，不挂编号。", until="1919-06-28", how="replaced"),
            _mem("France", "1815-06-09", "1815年6月9日起是成员。史页写1871年《法兰克福条约》之后不再是会员，没有写日，不设停止日。1919年6月28日凡尔赛条约写法国回到，前一行没有断开，不另开一行。"),
            _mem("Netherlands", "1815-06-09", "1815年6月9日起是成员。1919年6月28日以后史页仍把它算在成员里。"),
            _mem("Germany", "1919-06-28", "史页写凡尔赛条约这一天起德国取代各邦。1936年德国正式退出、1950年才回来，都只有年，不设停止日，所以1936年以后这一行仍显示。"),
            _mem("Switzerland", "1919-06-28", "史页写凡尔赛条约这一天起瑞士加入。"),
            _mem("Belgium", "1919-06-28", "史页写凡尔赛条约这一天起比利时加入。"),
            _mem("United Kingdom", "1919-06-28", "史页写凡尔赛条约这一天起英国加入。组织页写1993年离开，没有写日，不设停止日。"),
            _mem("Italy", "1919-06-28", "史页写凡尔赛条约这一天起意大利加入。史页写1936年正式退出，组织页写1935年放弃参加。两说都没有日，不择一，不设停止日。"),
            _mem("United States", "1945-11-20", "史页写1945年11月20日复会时有美国代表团，并写美国在战后是成员、1961年离开。1961年没有写日，不设停止日。"),
        ],
    }
    sign = (
        "国际计量局米制公约页把这一国列为1875年的最初签署方。页上没有写批准日或生效日，"
        "所以这一行只是签署方，不写成已经生效的缔约方。"
    )
    bipm = {
        "id": "bipm",
        "zh": "国际计量局（米制公约）",
        "en": "International Bureau of Weights and Measures",
        "type": "organization",
        "type_zh": "正式国际组织",
        "from": "1875-05-20",
        "until": None,
        "signed": "1875-05-20",
        "effective": None,
        "headquarters": [{"from": "1875-05-20", "text": "塞夫尔，布雷特伊馆。"}],
        "summary": (
            "米制公约页写：公约1875年5月20日签署，1921年修订，并设立国际计量局。"
            "公约对各国生效的日子这一页没有写，所以不填生效日。"
            "最初签署方按该页名单写入，后来的会籍不从签署推断。"
            "有完整加入日或除名日的，另按国际计量局页面写入。只有年月、没有日的不编。"
        ),
        "incomplete": True,
        "list_note": (
            "签署方不是生效后的缔约方名单。加入日只采用写到日的官方记载。"
            "摩洛哥、厄瓜多尔、白俄罗斯、爱沙尼亚、哥斯达黎加等只有年月，不编。"
            "退出和暂停：除多米尼加的除名日外，这一批没有写到日的记录，标无。"
        ),
        "sources": [
            {"label": "米制公约与最初签署方", "url": "https://www.bipm.org/en/metre-convention"},
            {"label": "国际计量局会员国", "url": "https://www.bipm.org/en/member-states"},
            {"label": "多米尼加的批准、除名和再加入", "url": "https://www.bipm.org/en/countries/do"},
            {"label": "国际计量委员会主席2014年报告", "url": "https://www.bipm.org/documents/20126/17315032/25th-CGPM-Report-of-CIPM-President-EN.pdf/3cf45835-d939-7577-fc8f-cc3f2ae2310b"},
            {"label": "国际计量委员会主席2018年报告", "url": "https://www.bipm.org/documents/20126/44023306/26th-CGPM-Report-of-CIPM-President-EN.pdf/a1aa6cf7-03ef-64a8-d958-af5a97a773b3"},
        ],
        "members": [
            _mem(name, "1875-05-20", sign, role="签署方")
            for name in (
                "Germany", "Argentina", "Austria-Hungary", "Belgium", "Brazil", "Denmark",
                "Spain", "United States of America", "France", "Italy", "Peru", "Portugal",
                "Russia", "Sweden and Norway", "Switzerland", "Türkiye", "Venezuela",
            )
        ] + [
            _mem("Dominican Republic", "1954-02-24", "国家页写1954年2月24日首次批准成为会员，2015年1月1日起被除名。", until="2015-01-01", how="removed"),
            _mem("Dominican Republic", "2026-04-09", "国家页写2026年4月9日再次加入。", hide_before=True),
            _mem("Tunisia", "2012-02-01", "国际计量委员会主席2014年报告：2012年2月1日加入。原为联系成员。"),
            _mem("Colombia", "2013-02-06", "国际计量委员会主席2014年报告：2013年2月6日加入。"),
            _mem("Iraq", "2013-08-20", "国际计量委员会主席2014年报告：2013年8月20日加入。"),
            _mem("Lithuania", "2015-04-16", "国际计量委员会主席2018年报告：2015年4月16日由联系成员转为公约缔约方。"),
            _mem("United Arab Emirates", "2015-04-27", "国际计量委员会主席2018年报告：2015年4月27日加入。"),
            _mem("Slovenia", "2016-03-23", "国际计量委员会主席2018年报告：2016年3月23日由联系成员转为公约缔约方。"),
            _mem("Montenegro", "2018-01-24", "国际计量委员会主席2018年报告：2018年1月24日由联系成员转为公约缔约方。"),
            _mem("Ukraine", "2018-08-07", "国际计量委员会主席2018年报告：2018年8月7日由联系成员转为公约缔约方。"),
            _mem("Peru", "2026-08-11", "会员国页写：秘鲁2026年8月11日加入，成为会员。1875年的签署不写成一直是会员。"),
            _mem("Azerbaijan", "2026-08-17", "会员国页写：阿塞拜疆2026年8月17日加入米制公约，成为会员。"),
        ],
    }
    ilo_note = "国际劳工组织太平洋新闻（2018年12月，刊在劳工组织网站）写的加入日。"
    ilo = {
        "id": "ilo",
        "zh": "国际劳工组织",
        "en": "International Labour Organization",
        "type": "organization",
        "type_zh": "正式国际组织",
        "from": "1919-06-28",
        "until": None,
        "signed": "1919-06-28",
        "effective": None,
        "headquarters": [{"from": "1919-06-28", "text": "1920年起在日内瓦。史页没有写迁入的日子。"}],
        "summary": (
            "劳工组织关于页写1919年创立，是凡尔赛条约的一部分。图书馆史页写和约于1919年6月28日通过，劳动条款成为章程。"
            "章程何时单独生效，这两页没有写成另一个日子，所以不填生效日。"
            "1976年图书馆文件列出29个创始会员和另外13个也被称作创始会员的国家，没有逐国写日。"
            "史页写这29国是批准凡尔赛条约后同时成为国联和劳工组织会员。加入日因此用联合国条约集里该国的国联加入日，不把1919年6月28日写成已经是会员。"
            "中国在国联名册里写明没有批准凡尔赛条约，创始名单虽有中国，这里不编。"
            "罗马尼亚的国联加入日两种记载，不择一，不编。"
        ),
        "incomplete": True,
        "list_note": (
            "名单不完整。创始会员的日子不是劳工组织单独的批准书，是条约集的国联加入日，依据是史页写的同时成为两边会员。"
            "中国、罗马尼亚不编。后来的加入仍只收写到日的。"
            "章程写退出通知两年后生效。这一批没有打开逐国通知日，退出标无。"
        ),
        "sources": [
            {"label": "国际劳工组织关于页", "url": "https://www.ilo.org/about-ilo"},
            {"label": "1919年创立说明", "url": "https://webapps.ilo.org/static/english/lib/century/"},
            {"label": "法律顾问：库克群岛和汤加的加入日", "url": "https://www.ilo.org/about-ilo/organizational-structure-international-labour-office/office-legal-adviser/institutional-governance-and-official-meetings"},
            {"label": "总干事报告：汤加2016年2月24日成为会员", "url": "https://www.ilo.org/media/199156/download"},
            {"label": "太平洋新闻里的加入日", "url": "https://www.ilo.org/media/413336/download"},
            {"label": "乌克兰1954年5月12日成为会员", "url": "https://www.ilo.org/sites/default/files/wcmsp5/groups/public/@europe/@ro-geneva/@sro-budapest/documents/publication/wcms_712299.pdf"},
        ],
        "members": [
            _mem(name, day, "1976年劳工组织图书馆文件列为创始会员。加入日用联合国条约集的国联加入日，因为史页写批准凡尔赛条约就同时成为国联和劳工组织会员。")
            for name, day in (
                ("Belgium", "1920-01-10"),
                ("Bolivia", "1920-01-10"),
                ("Brazil", "1920-01-10"),
                ("Canada", "1920-01-10"),
                ("Australia", "1920-01-10"),
                ("South Africa", "1920-01-10"),
                ("New Zealand", "1920-01-10"),
                ("India", "1920-01-10"),
                ("Cuba", "1920-03-08"),
                ("Czechoslovakia", "1920-01-10"),
                ("France", "1920-01-10"),
                ("Greece", "1920-03-30"),
                ("Guatemala", "1920-01-10"),
                ("Haiti", "1920-06-30"),
                ("Honduras", "1920-11-03"),
                ("Italy", "1920-01-10"),
                ("Japan", "1920-01-10"),
                ("Liberia", "1920-06-30"),
                ("Nicaragua", "1920-11-03"),
                ("Panama", "1920-11-25"),
                ("Peru", "1920-01-10"),
                ("Poland", "1920-01-10"),
                ("Portugal", "1920-04-08"),
                ("Serbo-Croatian-Slovene State", "1920-02-10"),
                ("Siam", "1920-01-10"),
                ("Uruguay", "1920-01-10"),
                ("Argentina", "1920-01-10"),
                ("Chile", "1920-01-10"),
                ("Colombia", "1920-02-16"),
                ("Denmark", "1920-03-08"),
                ("Netherlands", "1920-03-09"),
                ("Norway", "1920-03-09"),
                ("Paraguay", "1920-01-10"),
                ("Persia", "1920-01-10"),
                ("Salvador", "1920-03-10"),
                ("Spain", "1920-01-10"),
                ("Sweden", "1920-03-09"),
                ("Switzerland", "1920-03-08"),
                ("Venezuela", "1920-03-03"),
            )
        ] + [
            _mem("United Kingdom", "1920-01-10", "创始名单写 British Empire。条约集把联合王国、各自治领和英属印度分成不同会员，这一行只对联合王国，日子是1920年1月10日。"),
        ] + [
            _mem("Ukraine", "1954-05-12", "劳工组织出版物写：乌克兰苏维埃社会主义共和国1954年5月12日按章程第1条第3款成为会员，总干事同日发电通知。"),
            _mem("Fiji", "1974-04-19", ilo_note),
            _mem("Papua New Guinea", "1976-05-01", ilo_note),
            _mem("Solomon Islands", "1984-05-28", ilo_note),
            _mem("Kiribati", "2000-02-03", ilo_note),
            _mem("Vanuatu", "2003-05-22", ilo_note),
            _mem("Samoa", "2005-03-07", ilo_note),
            _mem("Marshall Islands", "2007-07-03", ilo_note),
            _mem("Tuvalu", "2008-05-27", ilo_note),
            _mem("Palau", "2012-05-29", ilo_note),
            _mem("Cook Islands", "2015-06-12", "法律顾问页写库克群岛2015年6月12日加入。太平洋新闻写同一天。"),
            _mem("Tonga", "2016-02-24", "总干事2016年2月报告写：接受书2016年2月24日收到，汤加同日成为第187个会员。法律顾问页写同一天。"),
        ],
    }
    for member in ilo["members"]:
        if member["name"] == "India":
            member["note"] += "国联名册写这一席是英属印度，不是1947年以后的印度共和国。对不上后来的印度就不挂。"
        if member["name"] == "South Africa":
            member["note"] += "国联名册写南非联邦。后来的南非共和国不回填。"
        if member["name"] == "Siam":
            member["note"] += "国联名册写暹罗。后来称泰国，改名日不在会员表上，不改名。"
        if member["name"] == "Persia":
            member["note"] += "国联名册写波斯。1935年起对外称伊朗，改名日不在会员表上，不改名。"
    return [(ccnr, "concert"), (bipm, "upu"), (ilo, "pca")]


def main():
    dip_path = CUR / "diplomacy.json"
    data = json.loads(dip_path.read_text(encoding="utf-8"))
    by_id = {org["id"]: org for org in data["orgs"]}

    members, stats = build_pca()
    pca_link = link_polities(members, lambda m: True)
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
        f"加入日当天能唯一对上政权编号的有{pca_link['linked']}行，对不上的{pca_link['unlinked']}行不挂。"
    )
    pca["sources"] = [
        {"label": "1899年公约缔约方（荷兰保存机关）", "url": "https://verdragenbank.overheid.nl/en/Treaty/Details/002330_p.html"},
        {"label": "1907年公约缔约方（荷兰保存机关）", "url": "https://verdragenbank.overheid.nl/en/Treaty/Details/003316_p.html"},
        {"label": "常设仲裁法院缔约方页", "url": "https://pca-cpa.org/en/about/introduction/contracting-parties/"},
        {"label": "1899年公约，美国国务院历史文件", "url": "https://history.state.gov/historicaldocuments/frus1902app2/d20"},
    ]

    upu = by_id["upu"]
    merged, ustats = build_upu(upu.get("members") or [])
    upu_link = link_polities(merged, lambda m: "页上现称" in (m.get("name") or ""))
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
        f"加入日当天能唯一对上政权编号的有{upu_link['linked']}行，对不上的{upu_link['unlinked']}行不挂。"
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
    extra_itu = [
        {
            "name": "南苏丹",
            "from": "2011-10-03",
            "track": "dated",
            "hide_before": True,
            "role": "成员国",
            "note": "国际电信联盟全权代表大会页面写：最近加入的会员是南苏丹，2011年10月3日加入。没有另写退出或暂停。",
        },
        {
            "name": "Kyrgyz Republic",
            "from": "1994-01-20",
            "track": "dated",
            "hide_before": True,
            "role": "成员国",
            "note": "1994年活动报告写：吉尔吉斯共和国于1994年1月20日交存《内罗毕公约》加入书后成为会员。退出、暂停无记录。",
        },
        {
            "name": "Republic of Tajikistan",
            "from": "1994-04-28",
            "track": "dated",
            "hide_before": True,
            "role": "成员国",
            "note": "1994年活动报告写：塔吉克斯坦共和国于1994年4月28日交存《内罗毕公约》加入书后成为会员。退出、暂停无记录。",
        },
        {"name": "Azerbaijani Republic", "from": "1992-04-10", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：阿塞拜疆共和国1992年4月10日交存《内罗毕公约》加入书后成为会员。"},
        {"name": "Republic of Estonia", "from": "1992-04-22", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：爱沙尼亚共和国1992年4月22日成为会员。"},
        {"name": "Republic of Croatia", "from": "1992-06-03", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：克罗地亚共和国1992年6月3日成为会员。"},
        {"name": "Republic of Slovenia", "from": "1992-06-16", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：斯洛文尼亚共和国1992年6月16日成为会员。"},
        {"name": "Republic of Armenia", "from": "1992-06-30", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：亚美尼亚共和国1992年6月30日成为会员。"},
        {"name": "Republic of Uzbekistan", "from": "1992-07-10", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：乌兹别克斯坦共和国1992年7月10日成为会员。"},
        {"name": "Republic of Moldova", "from": "1992-10-20", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：摩尔多瓦共和国1992年10月20日成为会员。"},
        {"name": "Republic of Bosnia and Herzegovina", "from": "1992-10-20", "track": "dated", "hide_before": True, "role": "成员国", "note": "1992年活动报告第2.1节：波斯尼亚和黑塞哥维那共和国1992年10月20日成为会员。"},
        {"name": "Republic of Georgia", "from": "1993-01-07", "track": "dated", "hide_before": True, "role": "成员国", "note": "1993年活动报告第2.1节：格鲁吉亚共和国1993年1月7日成为会员。"},
        {"name": "Republic of Kazakhstan", "from": "1993-02-23", "track": "dated", "hide_before": True, "role": "成员国", "note": "1993年活动报告第2.1节：哈萨克斯坦共和国1993年2月23日成为会员。"},
        {"name": "The Former Yugoslav Republic of Macedonia", "from": "1993-05-04", "track": "dated", "hide_before": True, "role": "成员国", "note": "1993年活动报告第2.1节：前南斯拉夫的马其顿共和国1993年5月4日成为会员。报告用的是当时的名称。"},
        {"name": "Turkmenistan", "from": "1993-05-07", "track": "dated", "hide_before": True, "role": "成员国", "note": "1993年活动报告第2.1节：土库曼斯坦1993年5月7日成为会员。"},
    ]
    have_key = {(m.get("name"), m.get("from")) for m in itu.get("members") or []}
    for row in extra_itu:
        if (row["name"], row["from"]) not in have_key:
            itu.setdefault("members", []).append(row)
    itu["incomplete"] = True
    itu_link = link_polities(
        itu.get("members") or [],
        lambda m: m.get("track") == "dated",
    )
    itu["list_note"] = (
        "名单不完整。20个签署方仍是签署方，后来的会籍未核，编号是1865年5月17日当时的政权。"
        "1992年活动报告写了八个新会员，其中前苏联和前南斯拉夫的新国家是阿塞拜疆、爱沙尼亚、克罗地亚、斯洛文尼亚、亚美尼亚、乌兹别克斯坦、摩尔多瓦、波黑。"
        "1993年活动报告里属于这两组的是格鲁吉亚、哈萨克斯坦、前南斯拉夫的马其顿共和国、土库曼斯坦。捷克、斯洛伐克不是这两组，不写进这一批。"
        "1994年活动报告写吉尔吉斯1994-01-20、塔吉克斯坦1994-04-28。南苏丹是2011年10月3日。"
        "这两份报告的成为会员名单里没有俄罗斯、乌克兰、白俄罗斯、拉脱维亚、立陶宛，不写继承。其余加入、退出、暂停无记录。"
        f"有加入日的行里挂上编号{itu_link['linked']}行，对不上的不挂。"
    )
    itu["summary"] = (
        "1865年5月17日，20个国家在巴黎签署国际电报公约，成立万国电报联盟。"
        "1932年马德里会议另订国际电信公约。改名生效日没有写到日，名称仍用万国电报联盟。"
        "1994年活动报告写吉尔吉斯1月20日、塔吉克斯坦4月28日成为会员。南苏丹2011年10月3日加入。"
        "其余后来的加入、退出、暂停和继承没有逐条的官方日子，不编。"
    )
    itu_sources = list(itu.get("sources") or [])
    for label, url in (
        ("国际电信联盟：南苏丹2011年10月3日加入", "https://www.itu.int/web/pp-18/en/article/itus-evolving-membership"),
        ("1994年活动报告：吉尔吉斯和塔吉克斯坦的加入日", "https://search.itu.int/history/HistoryDigitalCollectionDocLibrary/2.145.62.en.100.pdf"),
        ("1992年活动报告：新会员", "https://search.itu.int/history/HistoryDigitalCollectionDocLibrary/2.143.62.en.100.pdf"),
        ("1993年活动报告：新会员", "https://search.itu.int/history/HistoryDigitalCollectionDocLibrary/2.144.62.en.100.pdf"),
    ):
        if url not in {s["url"] for s in itu_sources}:
            itu_sources.append({"label": label, "url": url})
    itu["sources"] = itu_sources

    early_stats = {}
    for org, after in early_orgs():
        linked = link_polities(org["members"], lambda m: True)
        org["list_note"] += f"加入日或签署日当天能唯一对上政权编号的有{linked['linked']}行，对不上的{linked['unlinked']}行不挂。"
        _upsert(data, org, after)
        early_stats[org["id"]] = linked

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
    print("upu added", ustats, "link", upu_link)
    print("pca link", pca_link, "itu link", itu_link)
    print("early", early_stats)


if __name__ == "__main__":
    main()
