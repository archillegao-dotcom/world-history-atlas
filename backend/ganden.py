"""甘丹颇章 1912–1951 的面板，以及藏南、阿克赛钦样本点的声索说明。

只挂在点到的政权或样本点上。不把后来的职务套到清朝多边形，也不把声索画成另一块实控。
日期和原文出处写在每条 note 里。启用日没有核到的旗帜不补一个日子。
"""
from __future__ import annotations

from .timeutil import HDate

QID = "Q2444884"
ZONE_RESTORE = "tibet_ganden_1950"
ZONE_GAP = "tibet_unverified_1951"
ZONE_CHAMDO = "tibet_chamdo_1950"

# 样本框只用来识别点击，不是边界。
_LHASA = (90.9, 29.45, 91.4, 29.85)
_TAWANG = (91.55, 27.35, 92.15, 27.85)
_AKSAI = (78.5, 34.9, 79.5, 35.5)


def _in(box, lat, lon):
    if lat is None or lon is None:
        return False
    x0, y0, x1, y1 = box
    return x0 <= lon <= x1 and y0 <= lat <= y1


def _on(date, a, b):
    """a、b 为 YYYY-MM-DD，含首日、含末日。"""
    k = date.key()
    def key(s, end):
        y, m, d = (int(x) for x in s.split("-"))
        if end:
            return HDate(y, m, d).key()
        return HDate(y, m, d).key()
    return key(a, False) <= k <= key(b, True)


def point_note(date, lat, lon) -> str | None:
    """只在样本点、而且只在写明的年份里出现。没有点击坐标时不套到整个印度或中国。"""
    if _in(_LHASA, lat, lon) and _on(date, "1912-01-01", "1912-12-31"):
        return ("已知缺陷：1912年点选拉萨仍落到中华民国，是底图还没有单独几何，不是已经核实这一年由中华民国统治。"
                "1913年1月1日才被数据集单列。那个日期不是成立日，也不是划定的边界，更不是史实确证的易手日。"
                "本批不把后来的轮廓回贴到1912年，也不把这个缺陷写成已经修好。")
    if _in(_LHASA, lat, lon) and date.key() >= HDate(1959, 3, 28).key():
        return ("1959年3月28日国务院命令写「自即日起」解散西藏地方政府，由西藏自治区筹备委员会行使西藏地方政府职权。"
                "地图这一天回到中国多边形，只表示命令里的政权废除和管理标识，不是该日全境战线已经测过，也不是每一点的实控确证。"
                "不是1951年5月23日签署，也不是10月26日进驻拉萨。"
                "https://www.gov.cn/lssdjt/content_1832698.htm "
                "https://www.xizang.gov.cn/rsxz/lsyg/202306/t20230607_359663.html")
    if _in(_TAWANG, lat, lon) and _on(date, "1914-07-03", "1951-02-05"):
        return ("达旺样本：底图这一天若画在印度里，那是数据集的线，不是已经核实的实控，也不能当成麦克马洪线的实测。"
                "1951年2月6日以前不按今天的印度实控来写。印度人员进入达旺写在1951年2月6日，到1951年8月才写到有效管治。"
                "中国声索线南地区。本批没有声索多边形。1800年这里仍是清朝多边形，不套这句。"
                "https://www.claudearpi.in/wp-content/uploads/2021/02/2012-Sonia_Shukla_Integratig-Tawang.pdf")
    if _in(_TAWANG, lat, lon) and _on(date, "1951-02-06", "1951-07-31"):
        return ("达旺样本：1951年2月6日印度人员进入。1951年8月以前不写成整个达旺已经有效管治，更不是整个藏南在这一天易手。"
                "中国声索线南。声索不改涂底图。底图本来可能已经把这里画在印度里，所以颜色不一定在这一天变化。"
                "https://www.claudearpi.in/wp-content/uploads/2021/02/2012-Sonia_Shukla_Integratig-Tawang.pdf")
    if _in(_TAWANG, lat, lon) and date.key() >= HDate(1951, 8, 1).key():
        return ("达旺样本：1951年8月写到印度管治已经建立。这是月份，不是8月1日整个藏南易手，也不是麦克马洪线的实测。"
                "实际控制看底图颜色。中国声索线南地区，声索不另涂一层实控色。更早的年份不回写成今天这样。"
                "https://www.claudearpi.in/wp-content/uploads/2021/02/2012-Sonia_Shukla_Integratig-Tawang.pdf")
    if _in(_AKSAI, lat, lon) and _on(date, "1914-07-03", "1947-08-14"):
        return ("阿克赛钦样本：底图这一天的控制方以多边形为准。1957年9月修通公路的陈述不回写到这一天，也不写成中国实控。"
                "后来的印度声索、中国实控不套到这一天。")
    if _in(_AKSAI, lat, lon) and _on(date, "1947-08-15", "1957-08-31"):
        return ("阿克赛钦样本：1947年8月15日起底图把这个点画进中国多边形。这是数据集在英属印度结束时的画法，"
                "不是当天核实的易手，也不是1957年9月的公路。印度声索这块。声索不把底图改涂成印度。"
                "https://nehruarchive.in/documents/in-the-rajya-sabha-chinese-road-construction-in-ladakh-31-august-1959-z7g9y")
    if _in(_AKSAI, lat, lon) and date.key() >= HDate(1957, 9, 1).key():
        return ("阿克赛钦样本：尼赫鲁1959年8月31日在联邦院说，中方宣布叶城至噶大克公路于1957年9月修通。"
                "这是月份，不是9月1日整块阿克赛钦易手，也不是1947年8月15日那次变色。底图颜色是中国多边形，表示数据集里的实际控制。"
                "印度声索这块。声索不另涂一层。"
                "https://nehruarchive.in/documents/in-the-rajya-sabha-chinese-road-construction-in-ladakh-31-august-1959-z7g9y")
    return None


def _between(date, a, b):
    return _on(date, a, b)


def offices_at(date) -> list[dict]:
    rows = []
    if _between(date, "1913-01-01", "1933-12-17"):
        rows.append({"role": "达赖喇嘛（掌政）", "tag": "掌政", "power": True, "name": "十三世达赖喇嘛土登嘉措",
                     "span": "本图从1913年1月1日列到1933年12月17日",
                     "note": "去世日是1933年12月17日。1895年亲政早于这块多边形，不回写。甘丹颇章作为制度通常从1642年算起，本页只核1912–1951。",
                     "src": "https://www.dalailama.com/the-dalai-lama/events-and-awards/chronology-of-events"})
    elif _between(date, "1933-12-18", "1933-12-31"):
        rows.append({"role": "掌政", "tag": "未记录", "power": True, "name": "未记录",
                     "span": "1933年12月18日至1933年12月31日",
                     "note": "十三世达赖于1933年12月17日去世。摄政选举月份记到1934年1月，这一天没有核对到在任者。",
                     "src": "https://www.dalailama.com/the-dalai-lama/events-and-awards/chronology-of-events"})
    if _between(date, "1934-01-01", "1940-12-31"):
        rows.append({"role": "摄政", "tag": "摄政", "power": True, "name": "热振活佛",
                     "span": "1934年1月（日待考）起，1941年交卸（月份待考）",
                     "note": "1934年1月由民众大会选出，日待考。1940年及以前不把达扎写成已经摄政。",
                     "src": "https://www.tibetjustice.org/reports/chron.html"})
    elif _between(date, "1941-01-01", "1941-12-31"):
        rows.append({"role": "摄政", "tag": "摄政", "power": True, "uncertain": True, "name": "热振活佛",
                     "span": "1934年1月（日待考）起；1941年交卸，月份待考",
                     "note": "这一天落在交接年。月份未知，不能确定他是否仍在任。和达扎一起出现是日期精度不够，不是两人共治。",
                     "src": "https://www.tibetjustice.org/reports/chron.html"})
        rows.append({"role": "摄政", "tag": "摄政", "power": True, "uncertain": True, "name": "达扎活佛",
                     "span": "1941年接任，月份待考",
                     "note": "接任月份没有核到，不能确定这一天他是否已经接任。不写成与热振共治。汉文全名待考，不另造译名。",
                     "src": "https://www.tibetjustice.org/reports/chron.html"})
    if _between(date, "1942-01-01", "1950-11-16"):
        rows.append({"role": "摄政", "tag": "摄政", "power": True, "name": "达扎活佛",
                     "span": "1942年1月1日起按已接任书写，至1950年11月16日",
                     "note": "1941年的交接月份仍待考，不回写成1月1日已经接任。汉文全名待考，不另造译名。1950年11月17日起不再写成仍掌政。",
                     "src": "https://www.tibetjustice.org/reports/chron.html"})
    if _between(date, "1940-02-22", "1950-11-16"):
        rows.append({"role": "达赖喇嘛（已坐床，尚未亲政）", "tag": "尚未亲政", "power": False, "name": "十四世达赖喇嘛丹增嘉措",
                     "span": "1940年2月22日坐床至1950年11月16日",
                     "note": "坐床不是亲政。这一段不把他写成实际掌权者，也不借用总统或主席。",
                     "src": "https://www.dalailama.com/the-dalai-lama/events-and-awards/chronology-of-events"})
    if _between(date, "1950-11-17", "1959-03-27"):
        rows.append({"role": "达赖喇嘛（亲政）", "tag": "亲政", "power": True, "name": "十四世达赖喇嘛丹增嘉措",
                     "span": "1950年11月17日起",
                     "note": "亲政日来自达赖喇嘛办公室年表。1950年12月16日离开拉萨前往亚东，1951年8月17日回到拉萨，职务没有因此中断。1951年8月9日以后，旧轮廓不再写成全境仍由他实地控制；那不是说这块无人统治。",
                     "src": "https://www.dalailama.com/the-dalai-lama/events-and-awards/chronology-of-events"})
    return rows


_POLITY = ("政教合一的地方政权。噶厦是办事机构。不套用总统、主席、总理这些后来的职务。"
           "Wikidata 上没有起止时间的「神权政治」「绝对君主制」不作为这一天的核定政体。")

_FLAG = ("雪山狮子旗的启用日待考。不把没有日期的文件写成1912年或1913年当天的法定国旗，这一页不显示旗图。")


def _phase_note(date, zone) -> str:
    base = ("名称用甘丹颇章，不用现代国家的职务填空。通过、坐床、亲政、去世分开写。"
            "边界是 CShapes 的大致轮廓，精度只表示数据集有一条线，不是实测，也不是历史省界。")
    if zone == ZONE_GAP or (zone != ZONE_RESTORE and date.key() >= HDate(1951, 8, 9).key() and date.key() < HDate(1959, 3, 28).key()):
        return (base + GAP_NOTE +
                "协议1951年5月23日签署，第4条写现行政治制度不予变更，第17条写签字盖章后立即生效，那是法律文本，不是拉萨进驻。"
                "拉萨先遣1951年9月9日、主力1951年10月26日进驻，都不是全区变色。"
                "下列职务是地方政府的记录，不等于这块全境仍由他实地控制，也不换成中华人民共和国主席。"
                "https://zh.wikisource.org/zh-hans/中央人民政府和西藏地方政府关于和平解放西藏办法的协议 "
                "https://www.xizang.gov.cn/xwzx_406/ztzl_416/gdzt/66zn/dsj/201901/t20190117_51822.html "
                "https://da.xzdw.gov.cn/dayz/lsjz/201801/t20180108_151175.html")
    if zone == ZONE_RESTORE or _between(date, "1950-10-02", "1951-08-08"):
        return (base + "1950年10月2日起，底图不再把整块涂成中华人民共和国。这块沿用 CShapes 在1950年10月1日仍单列的西藏轮廓，不是新测的控制线。"
                "昌都战役10月6日开始、10月24日结束。10月24日起只把昌都大致框分开，拉萨不在同一天变色。"
                "https://www.xizang.gov.cn/xwzx_406/ztzl_416/gdzt/66zn/dsj/201901/t20190117_51822.html")
    return base + "1913年1月1日是 CShapes 开始单列的日期，不是成立日。"


# 灰色多边形的名称。未知的是几何范围，不是说当时无人统治。
GAP_NAME = "数据不足（旧轮廓，不是实控重建）"
GAP_NOTE = ("灰色只表示数据不足：没有逐点历史几何，不知道1951年8月9日以后实控画到哪里。"
            "8月9日只是新疆骑兵进驻噶大克的日子，一个城镇不能把中西部全区涂成已重建的实控。"
            "沿用的是更早的数据集轮廓。不是无人统治，也不是中华人民共和国的实控色。")

# 地图上的短标签。面板里仍用完整名称和说明。
_MAP_LABEL = {
    ZONE_RESTORE: "甘丹颇章",
    ZONE_GAP: "数据不足",
    ZONE_CHAMDO: "昌都大致框",
}


def feature_label(props) -> str | None:
    """地上的字。CShapes 711 和这三块不用 Wikidata 的「西藏」当标签。"""
    if not props:
        return None
    if props.get("CSHAPES") == 711:
        return "甘丹颇章"
    return _MAP_LABEL.get(props.get("ZONE"))


def applies(state_id, zone) -> bool:
    return state_id == QID or zone in (ZONE_RESTORE, ZONE_GAP)


def finish_regime(out: dict, polity, date, params) -> dict:
    props = (polity or {}).get("props") or {}
    zone = props.get("ZONE")
    note = point_note(date, params.get("lat"), params.get("lon"))
    if note and "样本" in note:
        note += " 虚线框是样本，不是实际边界。"
    if note:
        out["claim"] = note
    if zone == ZONE_CHAMDO:
        zh = props.get("NAME_ZH") or "昌都大致框（共军控制，不是辖境）"
        prev = out.get("geom_note") or ""
        if zh not in prev:
            out["geom_note"] = (zh + "。" + prev).strip()
    if not applies((out.get("state") or {}).get("id"), zone):
        return out
    st = out["state"]
    if zone == ZONE_GAP:
        st["name"] = GAP_NAME
        st["from"] = "1951年8月9日（不再沿用旧轮廓冒充实控；不是易手日）"
        st["to"] = "1959年3月28日（不含当天）"
        out["geom_note"] = GAP_NOTE
    else:
        st["name"] = "甘丹颇章"
        st["en"] = "Ganden Phodrang"
        st["from"] = "1913年1月1日（底图开始单列）"
        st["to"] = "不是1950年10月2日或1951年5月23日"
    st["flag"] = None
    st["flag_file"] = None
    st["flag_dated"] = False
    st["flag_note"] = _FLAG
    out["gov"] = []
    out["gov_undated"] = []
    out["gov_note"] = _POLITY
    out["ideology"] = []
    out["parties"] = []
    out["capital"] = ["拉萨"]
    out["definition"] = None
    out["definition_src"] = None
    out["profile_note"] = _phase_note(date, zone)
    prev = out.get("note") or ""
    out["note"] = (out["profile_note"] + " " + prev).strip()
    return out


def finish_leaders(out: dict, polity, date, params) -> dict:
    props = (polity or {}).get("props") or {}
    zone = props.get("ZONE")
    note = point_note(date, params.get("lat"), params.get("lon"))
    if note and "样本" in note:
        note += " 虚线框是样本，不是实际边界。"
    if note:
        out["claim"] = note
    if zone == ZONE_CHAMDO and out.get("territory"):
        zh = props.get("NAME_ZH") or "昌都大致框（共军控制，不是辖境）"
        prev = out["territory"].get("geom_note") or ""
        if zh not in prev:
            out["territory"]["geom_note"] = (zh + "。" + prev).strip()
    if not applies((out.get("state") or {}).get("id"), zone):
        return out
    rows = offices_at(date)
    out["curated_offices"] = rows
    out["heads"] = []
    out["offices"] = []
    out["undated_offices"] = []
    out["regents"] = []
    out["eras"] = []
    out["interregna"] = []
    # 未记录不计入。页签数字和名单是同一批人。
    out["total"] = sum(1 for r in rows if r.get("name") not in (None, "", "未记录"))
    if zone == ZONE_GAP and out.get("territory"):
        out["territory"]["geom_note"] = GAP_NOTE
    if out.get("state"):
        if zone == ZONE_GAP:
            out["state"]["name"] = GAP_NAME
        else:
            out["state"]["name"] = "甘丹颇章"
    prev = (out.get("note") or "").replace("这一日期没有找到带时间的任职记录。", "")
    out["note"] = ("职务只列本批核对过的达赖喇嘛和摄政。没有核对到的噶伦、代本写未记录，不借用中华民国或中华人民共和国的职位来填。"
                   + prev)
    return out
