"""特殊地位领土的类别说明（中文解释）。类别定义概括自英文维基百科对应条目（链接附在每个类别里，CC BY-SA）。"""
from __future__ import annotations

CATS = {
    "sar": ("特别行政区", "中华人民共和国根据「一国两制」设立的地方行政区域，除外交和国防外享有高度自治权，实行与内地不同的法律、经济和行政制度。",
            "https://en.wikipedia.org/wiki/Special_administrative_regions_of_China"),
    "crown": ("皇家属地", "英国王室的属地：不属于英国本土，也不是英国海外领地；内政自治，外交和国防由英国负责，君主是英国国王/女王。",
              "https://en.wikipedia.org/wiki/Crown_Dependencies"),
    "bot": ("英国海外领地", "在英国主权之下、但不属于英国本土的领土；多数有自己的地方政府，总督由英国君主任命，外交和国防由英国负责。",
            "https://en.wikipedia.org/wiki/British_Overseas_Territories"),
    "sba": ("英国主权基地区", "1960 年塞浦路斯独立时英国保留主权的军事基地区，属英国海外领地。",
            "https://en.wikipedia.org/wiki/Akrotiri_and_Dhekelia"),
    "us": ("美国属地（非建制领土）", "受美国主权管辖、但不属于任何一个州的领土；当地居民的权利由国会立法规定（如没有总统选举投票权）。",
           "https://en.wikipedia.org/wiki/Territories_of_the_United_States"),
    "fr_dom": ("法国海外省/大区", "与法国本土各省地位相同的海外行政区，属于法国和欧盟的一部分。",
               "https://en.wikipedia.org/wiki/Overseas_departments_and_regions_of_France"),
    "fr_com": ("法国海外集体/特殊地位领地", "法国主权下、拥有不同程度自治权的海外领土（如海外集体、新喀里多尼亚的特殊地位、无常住人口的领地）。",
               "https://en.wikipedia.org/wiki/Overseas_France"),
    "dk": ("丹麦王国自治领土", "丹麦王国的组成部分，享有广泛的地方自治（自治政府、议会），外交和国防主要由丹麦负责。",
           "https://en.wikipedia.org/wiki/Danish_Realm"),
    "aland": ("芬兰自治省", "芬兰主权下、以瑞典语为官方语言的非军事化自治地区，自治权由国际联盟 1921 年决议确认。",
              "https://en.wikipedia.org/wiki/%C3%85land"),
    "nor": ("挪威属地", "挪威主权下的特殊领土；斯瓦尔巴的主权由 1920 年《斯瓦尔巴条约》确认，缔约国公民享有平等的经济活动权利。",
            "https://en.wikipedia.org/wiki/Svalbard"),
    "nl": ("荷兰王国构成国", "荷兰王国内与荷兰本土地位平等的构成国，内政自治，外交和国防由王国负责。",
           "https://en.wikipedia.org/wiki/Kingdom_of_the_Netherlands"),
    "nz": ("新西兰自由联合邦", "与新西兰「自由联合」的自治国家：内政完全自治，居民是新西兰公民，新西兰协助其外交和国防。",
           "https://en.wikipedia.org/wiki/Realm_of_New_Zealand"),
    "au": ("澳大利亚外部领地", "不属于任何州的澳大利亚领土，由联邦政府直接管理。",
           "https://en.wikipedia.org/wiki/States_and_territories_of_Australia"),
    "hk_uk": ("英国属地（英属香港）", "英国管治时期的香港：香港岛 1842 年依《南京条约》割让，九龙半岛南部 1860 年依《北京条约》割让，"
              "新界 1898 年依《展拓香港界址专条》租借 99 年；由英国君主任命的总督管治（1983 年起称「英国属土」），1997 年 7 月 1 日移交中华人民共和国。",
              "https://en.wikipedia.org/wiki/British_Hong_Kong"),
    "mo_pt": ("葡萄牙管治地区（葡属澳门）", "葡萄牙人 16 世纪中叶起在澳门居留；1887 年《中葡和好通商条约》确认葡萄牙「永驻管理」澳门；"
              "1979 年中葡建交时葡萄牙承认澳门是由葡萄牙管理的中国领土；1999 年 12 月 20 日移交中华人民共和国。",
              "https://en.wikipedia.org/wiki/Portuguese_Macau"),
    "zone_holdout": ("实际控制区", "内战等冲突中，某一政权在对方已控制的领土范围内仍实际控制的地区（日期与范围见下方说明与 data/curated/control_zones.json）。",
                     "https://en.wikipedia.org/wiki/Chinese_Civil_War"),
    "zone_occupied": ("军事占领/接管地区", "战争中被一方军队占领并由其设立机构管理、但尚未有正式条约或行政区划安排的地区。",
                      "https://en.wikipedia.org/wiki/Military_occupation"),
    "zone_regime": ("当时的地位", "底图没有单独画出、在此补上的政权区域（如被画在殖民地整体之内的保护国、苏丹国）；地位与日期见下方说明（data/curated/control_zones.json，"
                    "依据英文维基等国际通行叙述），范围为今一级行政区或国界的近似。", "https://en.wikipedia.org/wiki/Protectorate"),
    "zone_de_facto": ("事实独立/自治地区", "没有普遍国际承认、但实际自行管治的地区。", "https://en.wikipedia.org/wiki/De_facto"),
    "disputed": ("主权争议地区", "主权归属有争议的地区；联合国将西撒哈拉列为「非自治领土」。地图按 Natural Earth 的「事实控制」画法单独画出，不代表对主权的立场。",
                 "https://en.wikipedia.org/wiki/Political_status_of_Western_Sahara"),
    "unverified": ("范围未核实", "两块近似多边形之间露出的底图空隙。没有核定控制方，外缘不是测过的边界。具体限制写在几何说明里。",
                   "https://www.nmgqq.com.cn/quqinggailan/jianzhiyange/xlglm/2022-11-28/25408.html"),
}

BY_NAME = {
    "Hong Kong S.A.R.": "sar", "Macao S.A.R": "sar", "Jersey": "crown", "Guernsey": "crown", "Isle of Man": "crown",
    "Akrotiri Sovereign Base Area": "sba", "Dhekelia Sovereign Base Area": "sba",
    "Puerto Rico": "us", "Guam": "us", "Northern Mariana Islands": "us", "American Samoa": "us", "United States Virgin Islands": "us",
    "French Guiana": "fr_dom", "Guadeloupe": "fr_dom", "Martinique": "fr_dom", "Reunion": "fr_dom", "Mayotte": "fr_dom",
    "New Caledonia": "fr_com", "French Polynesia": "fr_com", "Wallis and Futuna": "fr_com", "Saint Pierre and Miquelon": "fr_com",
    "Saint Barthelemy": "fr_com", "Saint Martin": "fr_com", "French Southern and Antarctic Lands": "fr_com", "Clipperton Island": "fr_com",
    "Greenland": "dk", "Faroe Islands": "dk", "Aland": "aland", "Svalbard": "nor", "Jan Mayen": "nor",
    "Aruba": "nl", "Curaçao": "nl", "Sint Maarten": "nl", "Cook Islands": "nz", "Niue": "nz",
    "Norfolk Island": "au", "Indian Ocean Territories": "au", "Heard Island and McDonald Islands": "au",
    "Western Sahara": "disputed", "Falkland Islands": "bot",
}


SOV_ZH = {"China": "中华人民共和国", "United Kingdom": "英国", "Portugal": "葡萄牙", "France": "法国", "Denmark": "丹麦",
          "Netherlands": "荷兰", "United States of America": "美国", "Australia": "澳大利亚", "New Zealand": "新西兰",
          "Norway": "挪威", "Finland": "芬兰"}


def unverified_note(polity, trans) -> str | None:
    """近似多边形之间的空隙没有对应政权。面板用几何说明，不用「没能对应」代替这段限制。"""
    props = (polity or {}).get("props") or {}
    if props.get("TERR_CAT") != "unverified":
        return None
    fid = props.get("fid")
    terr = getattr(trans, "terr", None) or []
    if not isinstance(fid, int):
        return None
    i = fid - 200000  # 与 backend/cshapes.py 的 OFF_TERR 相同
    if i < 0 or i >= len(terr):
        return None
    return terr[i].get("geom_note") or None


def info(name: str, cat: str | None = None) -> dict | None:
    k = cat if cat in CATS else BY_NAME.get(name, "bot")
    t, expl, url = CATS[k]
    return {"type": t, "explain": expl, "url": url}
