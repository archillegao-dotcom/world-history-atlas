"""
国家政权/国号更替链（1800 年至今）→ data/curated/regime_chains.json
每行：[起, 止(不含, None=至今), 中文名, 英文维基条目（来源，QID 由维基 API 解析）, 备注]
日期以英文维基百科条目信息框为准（国际通行史学叙述）；并立政权（如东西德、意大利社会共和国）用 parallel 标出。
用法：.venv/bin/python tools/curated_src/regime_chains.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from wpq import qids  # noqa: E402

CH = {
 "Q142": ("法国", [
  ["1792-09-22", "1804-05-18", "法兰西第一共和国", "French First Republic", "1799-11-10 起为执政府"],
  ["1804-05-18", "1814-04-06", "法兰西第一帝国", "First French Empire", None],
  ["1814-04-06", "1815-03-20", "法兰西王国（波旁复辟）", "Bourbon Restoration in France", None],
  ["1815-03-20", "1815-07-08", "法兰西第一帝国（百日王朝）", "Hundred Days", None],
  ["1815-07-08", "1830-08-09", "法兰西王国（波旁复辟）", "Bourbon Restoration in France", None],
  ["1830-08-09", "1848-02-24", "法兰西王国（七月王朝）", "July Monarchy", None],
  ["1848-02-24", "1852-12-02", "法兰西第二共和国", "French Second Republic", None],
  ["1852-12-02", "1870-09-04", "法兰西第二帝国", "Second French Empire", None],
  ["1870-09-04", "1940-07-10", "法兰西第三共和国", "French Third Republic", None],
  ["1940-07-10", "1944-08-25", "法兰西国（维希法国）", "Vichy France", "1940-06-22 停战后北部和西部海岸为德国占领区；1942-11-11 起全境被德意占领；伦敦另有「自由法国」"],
  ["1944-08-25", "1946-10-27", "法兰西共和国临时政府", "Provisional Government of the French Republic", "1944-06-03 成立于阿尔及尔，1944-08-25 巴黎解放后迁回"],
  ["1946-10-27", "1958-10-04", "法兰西第四共和国", "French Fourth Republic", None],
  ["1958-10-04", None, "法兰西第五共和国", "French Fifth Republic", None]]),
 "Q183": ("德国", [
  ["1800-01-01", "1806-08-06", "神圣罗马帝国", "Holy Roman Empire", None],
  ["1806-07-12", "1813-10-19", "莱茵邦联", "Confederation of the Rhine", "不含普鲁士、奥地利"],
  ["1815-06-08", "1866-08-23", "德意志邦联", "German Confederation", None],
  ["1867-07-01", "1871-01-18", "北德意志邦联", "North German Confederation", None],
  ["1871-01-18", "1918-11-09", "德意志帝国", "German Empire", None],
  ["1918-11-09", "1933-01-30", "德国（魏玛共和国）", "Weimar Republic", None],
  ["1933-01-30", "1945-06-05", "纳粹德国", "Nazi Germany", "1945-05-08 无条件投降生效"],
  ["1945-06-05", "1949-05-23", "盟军占领下的德国", "Allied-occupied Germany", "《柏林宣言》，四国占领区"],
  ["1949-05-23", "1990-10-03", "德意志联邦共和国（西德）", "West Germany", "parallel"],
  ["1949-10-07", "1990-10-03", "德意志民主共和国（东德）", "East Germany", "parallel"],
  ["1990-10-03", None, "德意志联邦共和国", "Germany", "两德统一"]]),
 "Q38": ("意大利", [
  ["1805-03-17", "1814-04-20", "意大利王国（拿破仑）", "Kingdom of Italy (Napoleonic)", None],
  ["1861-03-17", "1946-06-02", "意大利王国", "Kingdom of Italy", "1922-10-31 起墨索里尼执政"],
  ["1943-09-23", "1945-04-25", "意大利社会共和国", "Italian Social Republic", "parallel；德国扶植，意大利北部"],
  ["1946-06-02", None, "意大利共和国", "Italy", "1946-06-02 全民公投，06-18 最高法院公布结果"]]),
 "Q29": ("西班牙", [
  ["1800-01-01", "1808-07-06", "西班牙王国（波旁，西班牙帝国）", "Spanish Empire", None],
  ["1808-07-06", "1813-12-11", "西班牙王国（约瑟夫·波拿巴）", "Napoleonic Spain", "parallel；加的斯议会另立政府"],
  ["1813-12-11", "1833-09-29", "西班牙王国（费尔南多七世复位）", "Spanish Empire", None],
  ["1833-09-29", "1868-09-30", "西班牙王国（伊莎贝拉二世）", "Reign of Isabella II", None],
  ["1868-09-30", "1873-02-11", "西班牙（民主六年：临时政府、阿马德奥一世）", "Sexenio Democrático", None],
  ["1873-02-11", "1874-12-29", "西班牙第一共和国", "First Spanish Republic", None],
  ["1874-12-29", "1931-04-14", "西班牙王国（复辟）", "Spain under the Restoration", None],
  ["1931-04-14", "1939-04-01", "西班牙第二共和国", "Second Spanish Republic", "1936-07-17 起内战"],
  ["1936-10-01", "1975-11-20", "佛朗哥时期的西班牙", "Francoist Spain", "1936-10-01 布尔戈斯国民军政府；1939-04-01 内战结束"],
  ["1975-11-22", None, "西班牙王国", "Spain", "胡安·卡洛斯一世即位；1978-12-29 宪法生效"]]),
 "Q159": ("俄罗斯", [
  ["1721-11-02", "1917-03-15", "俄罗斯帝国", "Russian Empire", None],
  ["1917-03-15", "1917-09-14", "俄国临时政府", "Russian Provisional Government", None],
  ["1917-09-14", "1917-11-07", "俄罗斯共和国", "Russian Republic", None],
  ["1917-11-07", "1922-12-30", "俄罗斯苏维埃联邦社会主义共和国", "Russian Soviet Federative Socialist Republic", "1918–1922 内战"],
  ["1922-12-30", "1991-12-26", "苏联", "Soviet Union", None],
  ["1991-12-26", None, "俄罗斯联邦", "Russia", None]]),
 "Q148": ("中国", [
  ["1644-06-06", "1912-02-12", "清朝", "Qing dynasty", None],
  ["1912-01-01", "1912-04-01", "中华民国临时政府（南京）", "Provisional Government of the Republic of China (1912)", "parallel"],
  ["1912-03-10", "1928-06-15", "中华民国（北洋政府）", "Beiyang government", "1915-12-12–1916-03-22 袁世凯称帝（中华帝国）"],
  ["1925-07-01", "1948-05-20", "中华民国国民政府", "Nationalist government", "parallel 至 1928；1928-12-29 东北易帜后全国名义统一"],
  ["1948-05-20", None, "中华民国（宪政）", "Taiwan", "1949-12-07 迁台"],
  ["1949-10-01", None, "中华人民共和国", "China", None]]),
 "Q17": ("日本", [
  ["1603-03-24", "1868-01-03", "江户幕府", "Tokugawa shogunate", None],
  ["1868-01-03", "1947-05-03", "大日本帝国", "Empire of Japan", "1945-09-02 起盟军占领"],
  ["1945-09-02", "1952-04-28", "盟军占领下的日本", "Occupation of Japan", "parallel"],
  ["1947-05-03", None, "日本国", "Japan", "《日本国宪法》施行"]]),
 "Q36": ("波兰", [
  ["1807-07-22", "1815-06-09", "华沙公国", "Duchy of Warsaw", None],
  ["1815-06-09", "1915-08-05", "波兰王国（会议王国，俄国统治）", "Congress Poland", "parallel；1867 后实际并入俄国"],
  ["1815-10-18", "1846-11-16", "克拉科夫自由市", "Free City of Kraków", "parallel"],
  ["1916-11-05", "1918-11-11", "波兰王国（摄政，德奥扶植）", "Regency Kingdom of Poland", None],
  ["1918-11-11", "1939-10-06", "波兰第二共和国", "Second Polish Republic", "1939-09 德苏瓜分；流亡政府至 1990"],
  ["1939-10-06", "1945-05-08", "德国、苏联占领下的波兰", "Occupation of Poland (1939–1945)", "总督府等；见二战图层"],
  ["1944-07-22", "1945-06-28", "波兰民族解放委员会 / 临时政府", "Polish Committee of National Liberation", "PKWN 1944-07-22 成立，1945-01-01 改为临时政府"],
  ["1945-06-28", "1989-12-31", "波兰人民共和国", "Polish People's Republic", "1945-06-28 民族团结临时政府；国号 1952-07-22 正式定为波兰人民共和国"],
  ["1989-12-31", None, "波兰共和国（第三共和国）", "Poland", None]]),
 "Q40": ("奥地利", [
  ["1804-08-11", "1867-03-30", "奥地利帝国", "Austrian Empire", None],
  ["1867-03-30", "1918-11-12", "奥匈帝国", "Austria-Hungary", "1867 年妥协"],
  ["1918-11-12", "1919-09-10", "德意志奥地利共和国", "Republic of German-Austria", None],
  ["1919-09-10", "1934-05-01", "奥地利第一共和国", "First Austrian Republic", None],
  ["1934-05-01", "1938-03-13", "奥地利联邦国", "Federal State of Austria", None],
  ["1938-03-13", "1945-04-27", "纳粹德国（德奥合并）", "Anschluss", "奥地利被并入德国"],
  ["1945-04-27", "1955-07-27", "盟军占领下的奥地利", "Allied-occupied Austria", "1945-04-27 第二共和国临时政府成立；四国占领"],
  ["1955-07-27", None, "奥地利共和国", "Austria", "《奥地利国家条约》生效，占领结束"]]),
 "Q43": ("土耳其", [
  ["1299-07-27", "1922-11-01", "奥斯曼帝国", "Ottoman Empire", "1922-11-01 废除苏丹制"],
  ["1920-04-23", "1923-10-29", "土耳其大国民议会政府（安卡拉）", "Government of the Grand National Assembly", "parallel"],
  ["1923-10-29", None, "土耳其共和国", "Turkey", None]]),
 "Q36704": ("南斯拉夫", [
  ["1918-12-01", "1929-10-03", "塞尔维亚人、克罗地亚人和斯洛文尼亚人王国", "Kingdom of Serbs, Croats and Slovenes", None],
  ["1929-10-03", "1941-04-17", "南斯拉夫王国", "Kingdom of Yugoslavia", "1941-04-17 投降后流亡政府至 1945"],
  ["1941-04-17", "1945-05-15", "轴心国占领与瓜分的南斯拉夫", "Axis occupation of Yugoslavia", "克罗地亚独立国、德占塞尔维亚等，见二战图层"],
  ["1943-11-29", "1945-11-29", "南斯拉夫民主联邦", "Democratic Federal Yugoslavia", "parallel；1945-03-07 临时政府"],
  ["1945-11-29", "1963-04-07", "南斯拉夫联邦人民共和国", "Federal People's Republic of Yugoslavia", None],
  ["1963-04-07", "1992-04-27", "南斯拉夫社会主义联邦共和国", "Socialist Federal Republic of Yugoslavia", "1991-06-25 起斯洛文尼亚、克罗地亚等相继独立"],
  ["1992-04-27", "2003-02-04", "南斯拉夫联盟共和国", "Federal Republic of Yugoslavia", None],
  ["2003-02-04", "2006-06-05", "塞尔维亚和黑山", "Serbia and Montenegro", None]]),
}

titles = sorted({r[3] for _, rows in CH.values() for r in rows})
Q = qids(titles)
for t in titles:   # 多个标题重定向到同一页面时批量结果会互相覆盖：缺的逐个再查
    if not (Q.get(t) or (None, None))[1]:
        Q.update(qids([t]))
out = {"_doc": __doc__.strip(), "chains": {}}
miss = []
for cq, (zh, rows) in CH.items():
    lst = []
    for a, b, z, t, note in rows:
        q = (Q.get(t) or (None, None))[1]
        if not q:
            miss.append(t)
        lst.append({"from": a, "to": b, "zh": z, "qid": q, "parallel": bool(note and note.startswith("parallel")),
                    "note": (note[9:].lstrip("；") if note and note.startswith("parallel") else note) or None,
                    "src": "https://en.wikipedia.org/wiki/" + t.replace(" ", "_")})
    out["chains"][cq] = {"zh": zh, "rows": lst, "merge_country": cq not in ("Q148", "Q36704")}
p = ROOT / "data" / "curated" / "regime_chains.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", p, "rows", sum(len(c["rows"]) for c in out["chains"].values()), "missing qid:", miss)
for cq, c in out["chains"].items():
    print(cq, [(r["zh"], r["qid"]) for r in c["rows"]])
