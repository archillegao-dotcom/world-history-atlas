#!/usr/bin/env python3
"""1932–1945 日本扶植政权的名义辖区。

实控仍是既有占领层（县城与铁路的大致范围）。这里只加 kind=claim、as_polity=false 的虚线：
整省用 ENP-China 1912–1949 省界，有县名单的用 MCGD 1931 治所泰森多边形。
不画满洲国的省，不改满洲国多边形，不把名义辖区写成日军占领。

重复运行会先删掉 group=puppet_nominal 再写入。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZONES = ROOT / "data" / "curated" / "control_zones.json"
CSV = ROOT / "data" / "curated" / "geom" / "MCGD_Rep_V2.csv"
CELLS = ROOT / "data" / "curated" / "geom" / "roc_county_cells.geojson"

ENP = "https://www.virtualshanghai.net/Data/Tables?ID=198"
ZENODO = "https://zenodo.org/records/5721459"
WIKI = "https://zh.wikipedia.org/wiki/"
# 1939 年《鐵と鋼》讲演记录里的察南十县。宣化在该页印成「宜化」。
TETSU = "https://doi.org/10.2355/tetsutohagane1915.25.6_466"
HUBEI = "https://www.krzzjn.com/show-917-61486.html"
REFORM = WIKI + "中华民国维新政府"
PROV = WIKI + "中华民国临时政府_(1937年—1940年)"
WANG = WIKI + "汪精卫国民政府"
HUABEI = WIKI + "华北政务委员会"
CHANAN = WIKI + "察南自治政府"
JINBEI = WIKI + "晋北自治政府"
JIDONG = WIKI + "冀东防共自治政府"
# 华北各省公署的月日，取自余子道等对伪政权的记述转载。没有打开国史馆 PDF。
NORTH = "https://inf.qq.com/read/1044028848/8"

UNCHECKED = "未核对《中華民國史事紀要》。"
PROV_NOTE = (
    "名义省界。轮廓是 ENP-China 1912–1949 的该省线，和虚线省界同一套，不是伪政权新测的界，也不是今天的省界。"
    "大致。设立省公署不等于全省县城都在日军占领下。实控仍看既有占领层的县城与铁路，乡村实控待考。"
    "不改底图政权，不改阵营。满洲国各省不在这里。纪要里核对上的写在日期说明。没有写已核对的日子，仍是未核对。"
)
COUNTY_NOTE = (
    "名义辖区。每个县是 MCGD 1931 年治所的泰森多边形，裁在 ENP-China 历史省界上。"
    "大致，不是县界，也不是日军占领测绘。实控是县城与交通线，乡村待考。"
    "不改底图政权，不改阵营。" + UNCHECKED
)
# 满洲国期间不画这些省，也不用 1947 年东北九省回填。
FORBIDDEN = {
    "fengtian", "jilin", "heilongjiang", "rehe", "liaoning1947", "jilin1947",
    "heilongjiang1947", "hejiang", "nenjiang", "andong", "songjiang", "xingan", "liaobei",
}


def counties(rows, names, province):
    want = set(names)
    found = {}
    for row in rows:
        if row["Province_ZhT"] == province and row["Name_ZhT"] in want:
            found[row["Name_ZhT"]] = "mcgd:" + row["FID"]
    missing = [n for n in names if n not in found]
    if missing:
        raise SystemExit(f"缺县 {province}: {missing}")
    return [found[n] for n in names]


def claim(id_, name, qid, zh, frm, until, geom, dates_note, note, sources):
    if "roc_ids" in geom and FORBIDDEN & set(geom["roc_ids"]):
        raise SystemExit(f"拒绝满洲国省界: {id_}")
    return {
        "id": id_,
        "group": "puppet_nominal",
        "kind": "claim",
        "as_polity": False,
        "name_zh": name,
        "name_en": name,
        "controller": {"qid": qid, "zh": zh},
        "from": frm,
        "until": until,
        "geometry": geom,
        "approx": True,
        "dates_note": dates_note,
        "note": note,
        "sources": sources,
    }


def prov(pid):
    return {"roc_ids": [pid], "nosimplify": True}


def cells(ids):
    return {"roc_counties": ids, "nosimplify": True}


def main():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    chanan = counties(rows, ["宣化", "萬全", "懷安", "涿鹿", "蔚縣", "陽原", "赤城", "龍關", "延慶", "懷來"], "察哈爾")
    jinbei = counties(rows, ["大同", "懷仁", "應縣", "山陰", "朔縣", "平魯", "左雲", "右玉", "陽高", "天鎮", "渾源", "廣靈", "靈丘"], "山西")
    known = set()
    # 只读 id，避免把整份几何载进比较。
    raw_cells = CELLS.read_text(encoding="utf-8")
    for cid in chanan + jinbei:
        if f'"id":"{cid}"' not in raw_cells:
            raise SystemExit(f"县域没有这个 id: {cid}")
        known.add(cid)

    end_wang = "1945-08-16"
    end_meng = "1945-08-19"
    Z = []

    Z.append(claim(
        "puppet_nom_jiangsu_reform", "伪江苏省（维新政府名义省界）", "Q708865", "中华民国维新政府",
        "1938-05-23", "1940-03-30", prov("jiangsu"),
        "维新政府本身：民国二十七年一月至六月印页三〇〇（PDF第306页），页眉三月二十八日，标题日本军阀傀儡南京伪「中华民国维新政府」成立，梁鸿志等任伪职。已核对。伪江苏省1938-05-23在苏州成立，这一天的纪要页没有打开到省成立，省的日子仍未核对。1940-03-30起改记汪精卫国民政府。",
        PROV_NOTE + "省会在苏州。记述里到1940年4月有38个县公署，不是全省县名单，不逐县另画。苏北与苏南的分界待考。",
        [REFORM, ENP, "https://www.drnh.gov.tw/p/405-1003-13313,c169.php?Lang=zh-tw"],
    ))
    Z.append(claim(
        "puppet_nom_jiangsu_wang", "伪江苏省（汪精卫国民政府名义省界）", "Q696242", "汪精卫国民政府",
        "1940-03-30", end_wang, prov("jiangsu"),
        "1940-03-30 维新政府并入汪精卫国民政府。1940-07-01 改委员制，不把这一天写成新省界。收到1945-08-16，这一天是汪政权宣布解散，不是单独的省令。",
        PROV_NOTE + "省会仍按苏州记述，后来是否迁南京没有另核，不改线。",
        [WANG, REFORM, ENP],
    ))
    Z.append(claim(
        "puppet_nom_zhejiang_reform", "伪浙江省（维新政府名义省界）", "Q708865", "中华民国维新政府",
        "1938-06-22", "1940-03-30", prov("zhejiang"),
        "1938-05-17 开始筹备，不把筹备日写成已经成立。1938-06-22 在杭州成立，省长汪瑞闿。",
        PROV_NOTE + "成立时的记述是13个县公署，不是全省县名单，不逐县另画。",
        [REFORM, ENP],
    ))
    Z.append(claim(
        "puppet_nom_zhejiang_wang", "伪浙江省（汪精卫国民政府名义省界）", "Q696242", "汪精卫国民政府",
        "1940-03-30", end_wang, prov("zhejiang"),
        "1940-03-30 起改记汪精卫国民政府，收到1945-08-16。民国二十九年一月至六月印页四〇〇（PDF第408页），页眉三月三十日，这一页没有把成立写成标题。印页三八四（PDF第392页）页眉三月二十六日，写汪兆铭傀儡组织即将出现。日子不改。",
        PROV_NOTE,
        [WANG, ENP, "https://www.drnh.gov.tw/p/405-1003-13318,c169.php?Lang=zh-tw"],
    ))
    Z.append(claim(
        "puppet_nom_anhui_reform", "伪安徽省（维新政府名义省界）", "Q708865", "中华民国维新政府",
        "1938-10-28", "1940-03-30", prov("anhui"),
        "1938-07-02 开始筹备，不把筹备日写成已经成立。1938-10-28 在蚌埠成立，省长倪道烺。",
        PROV_NOTE + "省会在蚌埠，不是怀宁。",
        [REFORM, ENP],
    ))
    Z.append(claim(
        "puppet_nom_anhui_wang", "伪安徽省（汪精卫国民政府名义省界）", "Q696242", "汪精卫国民政府",
        "1940-03-30", end_wang, prov("anhui"),
        "1940-03-30 起改记汪精卫国民政府，收到1945-08-16。",
        PROV_NOTE + "省会仍记蚌埠。后来是否迁走没有另核，不改线。",
        [WANG, ENP],
    ))
    Z.append(claim(
        "puppet_nom_hubei_1939", "伪湖北省（名义省界，尚未归汪政权）", "local:puppet-hubei", "伪湖北省政府",
        "1939-11-05", "1940-10-03", prov("hubei"),
        "1939-11-05 在武昌成立，省长何佩瑢。不属维新政府，也不属临时政府。1940年10月划入汪政权，3日与5日两说，从10月3日起改记。10月1日、2日不另切。",
        PROV_NOTE + "代管河南信阳、湖南临湘和岳阳、江西九江和南昌一带。那些县不并进这块。代管县界待考。",
        [HUBEI, ENP],
    ))
    Z.append(claim(
        "puppet_nom_hubei_wang", "伪湖北省（汪精卫国民政府名义省界）", "Q696242", "汪精卫国民政府",
        "1940-10-03", end_wang, prov("hubei"),
        "1940-10-03 起改记汪精卫国民政府。另有10月5日一说，不把5日写成已经核对。收到1945-08-16。",
        PROV_NOTE + "代管县仍不并进。汉口特别市的市界待考，不另画。",
        [HUBEI, WANG, ENP],
    ))
    Z.append(claim(
        "puppet_nom_guangdong", "伪广东省（汪精卫国民政府名义省界）", "Q696242", "汪精卫国民政府",
        "1940-05-10", end_wang, prov("guangdong"),
        "1940-05-10 成立。陈公博兼任主席，陈耀祖代理。1938-12-10 的治安维持会和1939-11-20 的广州市公署不是省，不从那两天画全省。收到1945-08-16。",
        PROV_NOTE + "海南若落在这套广东轮廓里，没有另切。岛界和广州市界待考。设立日未见国史馆页码，标大致。",
        [WANG, ENP],
    ))
    Z.append(claim(
        "puppet_nom_hebei_prov", "伪河北省（临时政府名义省界）", "Q704714", "中华民国临时政府",
        "1938-02-01", "1940-03-30", prov("zhili"),
        "省公署在1938年1月，日待考，不从1月1日画。1938-02-01 冀东并入，原管辖地区复归河北，从这一天画。省长高凌霨。1940-03-30 起改记华北政务委员会。",
        PROV_NOTE + "用的是直隶改称河北之后的那条 ENP 线。北平、天津特别市不另切，市界待考。",
        [NORTH, PROV, JIDONG, ENP],
    ))
    Z.append(claim(
        "puppet_nom_hebei_ncp", "伪河北省（华北政务委员会名义省界）", "Q10905486", "华北政务委员会",
        "1940-03-30", end_wang, prov("zhili"),
        "1940-03-30 起。名义上属汪精卫国民政府，政务在华北政务委员会，不把整省写成南京直接省政。收到1945-08-16。",
        PROV_NOTE,
        [HUABEI, WANG, ENP],
    ))
    Z.append(claim(
        "puppet_nom_shandong_prov", "伪山东省（临时政府名义省界）", "Q704714", "中华民国临时政府",
        "1938-03-05", "1940-03-30", prov("shandong"),
        "1938-03-05 在济南成立，省长马良。1940-03-30 起改记华北政务委员会。",
        PROV_NOTE,
        [NORTH, PROV, ENP],
    ))
    Z.append(claim(
        "puppet_nom_shandong_ncp", "伪山东省（华北政务委员会名义省界）", "Q10905486", "华北政务委员会",
        "1940-03-30", end_wang, prov("shandong"),
        "1940-03-30 起改记华北政务委员会，收到1945-08-16。",
        PROV_NOTE,
        [HUABEI, ENP],
    ))
    Z.append(claim(
        "puppet_nom_shanxi_prov", "伪山西省（临时政府名义省界）", "Q704714", "中华民国临时政府",
        "1938-06-27", "1940-03-30", prov("shanxi"),
        "1938-06-27 在阳曲成立，省长苏体仁。1940-03-30 起改记华北政务委员会。",
        PROV_NOTE + "晋北十三县在1939-09-01前另有晋北自治政府。这块不挖那些县，分界待考。阎锡山的省实控填色不改。",
        [NORTH, PROV, JINBEI, ENP],
    ))
    Z.append(claim(
        "puppet_nom_shanxi_ncp", "伪山西省（华北政务委员会名义省界）", "Q10905486", "华北政务委员会",
        "1940-03-30", end_wang, prov("shanxi"),
        "1940-03-30 起改记华北政务委员会，收到1945-08-16。",
        PROV_NOTE + "晋北政厅的十三个县另见虚线，不从全省里挖。",
        [HUABEI, ENP],
    ))
    Z.append(claim(
        "puppet_nom_henan_prov", "伪河南省（临时政府名义省界）", "Q704714", "中华民国临时政府",
        "1938-05-01", "1940-03-30", prov("henan"),
        "1938-05-01 在安阳成立，省长萧瑞臣。开封1938-06-06才陷落，不把5月1日写成开封已经易手。1940-03-30 起改记华北政务委员会。",
        PROV_NOTE + "省会在安阳，不是开封。",
        [NORTH, PROV, ENP],
    ))
    Z.append(claim(
        "puppet_nom_henan_ncp", "伪河南省（华北政务委员会名义省界）", "Q10905486", "华北政务委员会",
        "1940-03-30", end_wang, prov("henan"),
        "1940-03-30 起改记华北政务委员会，收到1945-08-16。",
        PROV_NOTE + "省会仍记安阳。后来是否迁开封没有另核，不改线。",
        [HUABEI, ENP],
    ))

    Z.append(claim(
        "puppet_nom_chanan", "察南自治政府（名义辖区）", "local:chanan", "察南自治政府",
        "1937-09-04", "1939-09-01", cells(chanan),
        "十县：宣化、万全、怀安、涿鹿、蔚县、阳原、赤城、龙关、延庆、怀来。1939-09-01 并入蒙疆联合自治政府，改察南政厅。民国二十六年七月至十二月印页三九三（PDF第401页），页眉九月四日，写日本帝国会议和北支那方面军，没有察南自治政府成立。日子不改。这一条没有核对上。",
        COUNTY_NOTE + "1939年《鐵と鋼》讲演记录列了这十县。不拿察哈尔全省代替。",
        [CHANAN, TETSU, ZENODO, ENP],
    ))
    Z.append(claim(
        "puppet_nom_chanan_office", "察南政厅（名义辖区）", "Q697837", "蒙疆联合自治政府",
        "1939-09-01", end_meng, cells(chanan),
        "1939-09-01 起为察南政厅。1943年改称宣化省，月日待考，县名单没有另一次核实，不另画。收到1945-08-19，与既有蒙疆层同一天，不是停战文书的生效时刻。",
        COUNTY_NOTE + "盟界待考，不画。",
        [CHANAN, WIKI + "蒙疆联合自治政府", ZENODO],
    ))
    Z.append(claim(
        "puppet_nom_jinbei", "晋北自治政府（名义辖区）", "local:jinbei", "晋北自治政府",
        "1937-10-15", "1939-09-01", cells(jinbei),
        "十三县：大同、怀仁、应县、山阴、朔县、平鲁、左云、右玉、阳高、天镇、浑源、灵丘、广灵。已核对：民国二十六年七月至十二月印页五五〇（PDF第558页），页眉十月十五、十六日，标题伪「晋北自治政府」成立于大同，夏恭出任最高委员伪职。不把十六日另写成成立日。1939-09-01 改晋北政厅。",
        COUNTY_NOTE + "县名单见中文维基百科《晋北自治政府》，该页引《山西文史资料》。不拿山西全省代替。",
        [JINBEI, ZENODO, ENP, "https://www.drnh.gov.tw/p/405-1003-13312,c169.php?Lang=zh-tw"],
    ))
    Z.append(claim(
        "puppet_nom_jinbei_office", "晋北政厅（名义辖区）", "Q697837", "蒙疆联合自治政府",
        "1939-09-01", end_meng, cells(jinbei),
        "1939-09-01 起为晋北政厅。1943年改称大同省，月日待考，县名单没有另一次核实，不另画。收到1945-08-19。",
        COUNTY_NOTE,
        [JINBEI, WIKI + "蒙疆联合自治政府", ZENODO],
    ))

    doc = json.loads(ZONES.read_text(encoding="utf-8"))
    kept = [z for z in doc["zones"] if z.get("group") != "puppet_nominal"]
    by_id = {z["id"]: z for z in kept}
    east = by_id["sjw_east_hebei"]
    east["dates_note"] = (
        "1935-11-25 殷汝耕在通州成立「冀东防共自治委员会」。已核对：民国二十四年十一月至十二月印页三四八（PDF第356页），页眉十一月二十五日，外交部电报写该委员会已于下午五时在通县宣告成立。12月25日改称政府：印页六五四（PDF第662页）页眉是十二月二十六日，写冀察政务委员会，没有改称。不另切。"
        "1938-02-01 并入：印页一四五（PDF第152页）页眉二月一日，写的是教育部，没有冀东。印页一四六（PDF第153页）页眉二月一、二日，注文写冀东二十二县编入河北省，省公署设于天津。这是注文，不是二月一日的标题。日子不改。实控没有另测点线，乡村待考。"
    )
    east["note"] = (
        "22县是名义辖区，不是日军占领测绘。县名单是1933年非武装区两专区。"
        "每个县是1931年治所的泰森多边形。大致，不是县界。县城和铁路以外的实控待考。"
    )
    for src in (JIDONG, "https://www.drnh.gov.tw/p/405-1003-13305,c169.php?Lang=zh-tw", "https://www.drnh.gov.tw/p/405-1003-13313,c169.php?Lang=zh-tw"):
        if src not in east["sources"]:
            east["sources"].append(src)
    m1937 = by_id["sjw_mengjiang_1937"]
    m1937["note"] = (
        "范围为手绘近似：察哈尔、绥远（包头以东）与晋北大同一带；河套地区仍由傅作义部（国民革命军）控制。"
        "察南十县、晋北十三县的名义辖区另见虚线，不从这块里挖。五个盟的盟界待考，不拿察哈尔或绥远全省代替。"
        "1937-10-28：民国二十六年七月至十二月印页五七八（PDF第586页），页眉十月二十八日，没有蒙古联盟自治政府成立的标题。日子不改。"
        "这块仍是大致范围，不是省界。大致。县域为治所泰森多边形近似。"
    )
    m1939 = by_id["sjw_mengjiang"]
    m1939["note"] = (
        "范围为手绘近似（±80 km）。东缘没有向外延伸。北纬45.4度、东经118.8度一带，名义隶属和现代旗界不够证明1944年实地控制，没有并进这条折线，另标为未核实的空隙。"
        "察南政厅、晋北政厅的县名单另见虚线。盟界待考。这块不是省界。"
        "大致。县域为治所泰森多边形近似。"
    )
    m1939["dates_note"] = (
        "1939-09-01 成立，首都张家口。1941-08-04 起对内称蒙古自治邦，这一日没有另核，不另切。"
        "1945-08 苏蒙联军进攻后瓦解。结束日仍是1945-08-19。"
    )
    doc["zones"] = kept + Z
    text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    if "解放军" in text[text.find("puppet_nom"):] or "解放区" in "".join(z["name_zh"] for z in Z):
        raise SystemExit("用词不合：名义层不得写解放军或解放区")
    ZONES.write_text(text, encoding="utf-8")
    print("puppet nominal", len(Z), "total", len(doc["zones"]))
    print("chanan", len(chanan), "jinbei", len(jinbei))


if __name__ == "__main__":
    main()
