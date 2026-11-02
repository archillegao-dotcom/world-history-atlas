"""v0.6.1 君主空档核对（data/audit/leader_gaps.md）的人工判定数据。
人物用英文维基条目名标识，QID 由 tools/curated_src/gap_fixes.py 用 wbgetentities(sites=enwiki) 解析并核对（结果存 data/curated/gap_qids.json）；
直接写 QID 的（"Q..."）同样经 wbgetentities 核对存在、标签相符。
日期：在位起止按所注英文维基百科条目（其依据为学界通行年表）；d=0 只精确到月，m=0 只精确到年。
A：缺失的君主任职记录（类别 a）→ extra_offices.json 的 extra_holders
B：真实的空位期 / 摄政 / 共治（类别 b）→ interregna.json（经 tools/curated_src/interregna.py）
C、Dd：类别 c / d 的判定与理由（只写进 data/audit/gap_resolutions.json）"""
import re
W = "https://en.wikipedia.org/wiki/"
def D(y, m=0, d=0):
    return {"y": y, "m": m, "d": d}
A = []   # (state, office_en, person, from, to, note)
def a(state, office, person, frm, to, note=None, src=None):
    A.append({"state": state, "office": office, "person": person, "from": frm, "to": to, "note": note,
              "src": src or (W + person.replace(" ", "_") if not re.match(r"^Q\d+$", person) else None)})
NAP, SIC, SAR = "Q173065", "Q188586", "Q165154"
LN = W + "List_of_monarchs_of_Naples"; LS = W + "List_of_monarchs_of_Sicily"
# 那不勒斯国王 1386–1734、1759–1806（本地数据此段整段缺失）
for p, f, t in [("Ladislaus of Naples", D(1386, 2, 24), D(1414, 8, 6)), ("Joanna II of Naples", D(1414, 8, 6), D(1435, 2, 2)),
                ("René of Anjou", D(1435, 2, 2), D(1442, 6, 2)), ("Alfonso V of Aragon", D(1442, 6, 2), D(1458, 6, 27)),
                ("Ferdinand I of Naples", D(1458, 6, 27), D(1494, 1, 25)), ("Alfonso II of Naples", D(1494, 1, 25), D(1495, 1, 23)),
                ("Ferdinand II of Naples", D(1495, 1, 23), D(1496, 10, 7)), ("Frederick of Naples", D(1496, 10, 7), D(1501, 8, 2)),
                ("Louis XII", D(1501, 8, 2), D(1504, 1, 31)), ("Ferdinand II of Aragon", D(1504, 1, 31), D(1516, 1, 23)),
                ("Joanna of Castile", D(1516, 1, 23), D(1555, 4, 12)), ("Charles V, Holy Roman Emperor", D(1516, 1, 23), D(1554, 7, 25)),
                ("Philip II of Spain", D(1554, 7, 25), D(1598, 9, 13)), ("Philip III of Spain", D(1598, 9, 13), D(1621, 3, 31)),
                ("Philip IV of Spain", D(1621, 3, 31), D(1665, 9, 17)), ("Charles II of Spain", D(1665, 9, 17), D(1700, 11, 1)),
                ("Philip V of Spain", D(1700, 11, 1), D(1707, 7, 7)), ("Charles VI, Holy Roman Emperor", D(1707, 7, 7), D(1734, 5, 10)),
                ("Ferdinand I of the Two Sicilies", D(1759, 10, 6), D(1806, 3, 30))]:
    a(NAP, "King of Naples", p, f, t, "那不勒斯国王（1504–1707 年与西班牙王位共主，1707/1714–1734 年属奥地利哈布斯堡）", LN)
# 西西里国王 1412–1458、1468–1713、1720–1734
for p, f, t in [("Ferdinand I of Aragon", D(1412, 6, 28), D(1416, 4, 2)), ("Alfonso V of Aragon", D(1416, 4, 2), D(1458, 6, 27)),
                ("Ferdinand II of Aragon", D(1468), D(1516, 1, 23)), ("Joanna of Castile", D(1516, 1, 23), D(1555, 4, 12)),
                ("Charles V, Holy Roman Emperor", D(1516, 1, 23), D(1556, 1, 16)), ("Philip II of Spain", D(1556, 1, 16), D(1598, 9, 13)),
                ("Philip III of Spain", D(1598, 9, 13), D(1621, 3, 31)), ("Philip IV of Spain", D(1621, 3, 31), D(1665, 9, 17)),
                ("Charles II of Spain", D(1665, 9, 17), D(1700, 11, 1)), ("Philip V of Spain", D(1700, 11, 1), D(1713, 4, 11)),
                ("Charles VI, Holy Roman Emperor", D(1720, 2, 17), D(1734))]:
    a(SIC, "King of Sicily", p, f, t, "西西里国王（1412–1516 年与阿拉贡、1516–1713 年与西班牙王位共主）", LS)
a(SAR, "King of Sardinia", "Charles II of Spain", D(1665, 9, 17), D(1700, 11, 1), "撒丁国王（与西班牙王位共主）", W + "List_of_monarchs_of_Sardinia")
# 中世纪意大利国王（加洛林王朝）
IT = "Q5343710"; LI = W + "King_of_Italy"
for p, f, t, n in [("Charlemagne", D(774, 6), D(814, 1, 28), "伦巴第国王（774 年攻陷帕维亚）"), ("Pepin of Italy", D(781, 4, 15), D(810, 7, 8), "意大利国王（查理曼之子，从属国王）"),
                   ("Bernard of Italy", D(813), D(818, 4, 17), "意大利国王"), ("Lothair I", D(818), D(855, 9, 29), "意大利国王"),
                   ("Louis II of Italy", D(844), D(875, 8, 12), "意大利国王"), ("Charles the Bald", D(875, 12), D(877, 10, 6), "意大利国王"),
                   ("Carloman of Bavaria", D(877), D(879), "意大利国王"), ("Charles the Fat", D(879), D(887, 11), "意大利国王"),
                   ("Rudolph II of Burgundy", D(922), D(926), "意大利国王"), ("Hugh of Italy", D(926, 7), D(947, 4, 10), "意大利国王")]:
    a(IT, "List of rulers of Italy", p, f, t, n, LI)
# 马穆鲁克苏丹（布尔吉王朝）
MAM = "Q282428"; LM = W + "List_of_Mamluk_sultans"
for p, f, t in [("An-Nasir Hasan", D(1354, 10), D(1361, 3)), ("Barquq", D(1382, 11, 26), D(1389, 6)), ("Barquq", D(1390, 2), D(1399, 6, 20)),
                ("Al-Mu'ayyad Shaykh", D(1412, 11, 6), D(1421, 1, 13)), ("Al-Muzaffar Ahmad", D(1421, 1), D(1421, 8)),
                ("Sayf ad-Din Tatar", D(1421, 8), D(1421, 11)),
                ("Barsbay", D(1422, 4), D(1438, 6, 7)), ("Al-Aziz Jamal al-Din Yusuf", D(1438, 6), D(1438, 9)), ("Sayf ad-Din Jaqmaq", D(1438, 9), D(1453, 2)),
                ("Al-Mansur Uthman", D(1453, 2), D(1453, 3)), ("Sayf ad-Din Inal", D(1453, 3), D(1461, 2)), ("Al-Mu'ayyad Ahmad", D(1461, 2), D(1461, 6)),
                ("Sayf al-Din Khushqadam", D(1461, 6), D(1467, 10)), ("Sayf ad-Din Bilbay", D(1467, 10), D(1467, 12)), ("Timurbugha", D(1467, 12), D(1468, 1)),
                ("Qaitbay", D(1468, 1), D(1496, 8)), ("An-Nasir Muhammad ibn Qaitbay", D(1496, 8), D(1498, 10)),
                ("Abu Sa'id Qansuh", D(1498, 10), D(1500, 6)), ("Al-Ashraf Janbalat", D(1500, 6), D(1501, 1)),
                ("Al-Ashraf Qansuh al-Ghawri", D(1501, 4), D(1516, 8, 24)), ("Tuman bay II", D(1516, 10), D(1517, 4, 15))]:
    a(MAM, "Sultan of Egypt", p, f, t, "马穆鲁克苏丹", LM)
# 德里苏丹
DEL = "Q229411"; LD = W + "List_of_monarchs_of_Delhi_Sultanate"
for p, f, t in [("Alauddin Khalji", D(1296, 7, 19), D(1316, 1, 4)), ("Shihabuddin Omar", D(1316, 1), D(1316, 4)),
                ("Qutbuddin Mubarak Shah", D(1316, 4), D(1320, 5)), ("Khusro Khan", D(1320, 5), D(1320, 9)),
                ("Ghiyath al-Din Tughluq", D(1320, 9), D(1325, 2)), ("Muhammad bin Tughluq", D(1325, 2), D(1351, 3, 20)),
                ("Firuz Shah Tughlaq", D(1351, 3, 23), D(1388, 9, 20)), ("Tughluq Khan", D(1388, 9), D(1389, 2)), ("Abu Bakr Shah", D(1389, 2), D(1390)),
                ("Mahmud Shah II", D(1394, 3), D(1412, 2)), ("Daulat Khan Lodi", D(1412), D(1414, 5)), ("Khizr Khan", D(1414, 5, 28), D(1421, 5, 20))]:
    a(DEL, "Sultan", p, f, t, "德里苏丹", LD)
# 匈牙利
HU = "Q171150"; LH = W + "List_of_Hungarian_monarchs"
for p, f, t, n in [("Béla III of Hungary", D(1172, 3, 4), D(1196, 4, 23), None), ("Louis I of Hungary", D(1342, 7, 21), D(1382, 9, 10), None),
                   ("Mary, Queen of Hungary", D(1386, 2, 24), D(1395, 5, 17), "1386 年查理二世遇刺后复位"),
                   ("Ladislaus the Posthumous", D(1440, 5, 15), D(1457, 11, 23), "1440 年 5 月 15 日加冕；本地原记录只精确到年，被同年精确到日的瓦迪斯瓦夫一世记录截断"),
                   ("Matthias, Holy Roman Emperor", D(1608, 6, 25), D(1619, 3, 20), "1608 年 6 月 25 日《利本条约》鲁道夫二世让出匈牙利（11 月 19 日加冕）"),
                   ("Leopold II, Holy Roman Emperor", D(1790, 2, 20), D(1792, 3, 1), "约瑟夫二世 1790 年 2 月 20 日去世即继位（11 月 15 日加冕）")]:
    a(HU, "King of Hungary", p, f, t, n, LH)
a("Q186096", "Tsar of Russia", "Alexis of Russia", D(1645, 7, 13), D(1676, 2, 8))
# 神圣罗马帝国：罗马人的国王（当选至加冕皇帝之间、以及从未加冕的国王）
HRE = "Q12548"; LK = W + "King_of_the_Romans"
for p, f, t in [("Otto III, Holy Roman Emperor", D(983, 12, 25), D(1002, 1, 23)), ("Conrad II, Holy Roman Emperor", D(1024, 9, 8), D(1039, 6, 4)),
                ("Henry III, Holy Roman Emperor", D(1039, 6, 4), D(1056, 10, 5)), ("Henry IV, Holy Roman Emperor", D(1056, 10, 5), D(1105, 12, 31)),
                ("Lothair III, Holy Roman Emperor", D(1125, 8, 30), D(1137, 12, 4)), ("Adolf, King of the Romans", D(1292, 5, 5), D(1298, 6, 23)),
                ("Henry VII, Holy Roman Emperor", D(1308, 11, 27), D(1313, 8, 24)), ("Louis IV, Holy Roman Emperor", D(1314, 10, 20), D(1347, 10, 11)),
                ("Frederick the Fair", D(1314, 10, 19), D(1330, 1, 13)), ("Charles IV, Holy Roman Emperor", D(1346, 7, 11), D(1378, 11, 29)),
                ("Wenceslaus IV of Bohemia", D(1376, 6, 10), D(1400, 8, 20)), ("Rupert, King of Germany", D(1400, 8, 21), D(1410, 5, 18)),
                ("Jobst of Moravia", D(1410, 10, 1), D(1411, 1, 18)), ("Sigismund, Holy Roman Emperor", D(1410, 9, 20), D(1437, 12, 9)),
                ("Ferdinand I, Holy Roman Emperor", D(1531, 1, 5), D(1558, 3, 14)), ("Ferdinand III, Holy Roman Emperor", D(1636, 12, 22), D(1657, 4, 2))]:
    a(HRE, "King of the Romans", p, f, t, "罗马人的国王（德意志国王）", LK)
a("Q179293", "monarch of Castile", "Urraca of León and Castile", D(1109, 7, 1), D(1126, 3, 8))
a("Q2114397", "Sultan of Yogyakarta", "Hamengkubuwono IX", D(1940, 3, 18), D(1988, 10, 2))
a("Q213467", "Raja of Perlis", "Q20452145", D(1897), D(1905), "玻璃市拉惹 Syed Saffi Jamalullail（1897–1905）", W + "Raja_of_Perlis")
a("Q1071439", "King of Imerina", "Radama II", D(1861, 8, 16), D(1863, 5, 12))
a("Q1071439", "King of Imerina", "Rasoherina", D(1863, 5, 12), D(1868, 4, 1))
a("Q207521", "Emperor of Ethiopia", "Tekle Giyorgis II", D(1868, 6), D(1871, 7, 11))
a("Q1747689", "Roman emperor", "Honorius (emperor)", D(395, 1, 17), D(423, 8, 15), "西罗马皇帝")
a("Q1747689", "Roman emperor", "Arcadius", D(395, 1, 17), D(408, 5, 1), "东罗马皇帝")
a("Q83891", "Sasanian", "Bahram V", D(420), D(438))
a("Q83891", "Sasanian", "Kavad I", D(498), D(531, 9, 13), "第二次在位（498/499–531）")
a("Q83891", "Sasanian", "Boran", D(631), D(632), "第二次在位")
a("Q10800789", "emperor", "Q2988059", D(1442, 9), D(1459, 10), "黎仁宗（1442–1459 在位，1453 年前由母后阮氏英摄政）", W + "Lê_Nhân_Tông")
a("Q12557", "khan", "Q8659", D(1329, 2, 27), D(1329, 8, 30), "元明宗和世㻋 1329 年 2 月在漠北即位，8 月暴卒", W + "Khutughtu_Khan")
a("Q917", "King of Bhutan", "Jigme Dorji Wangchuck", D(1952, 3, 30), D(1972, 7, 21), "1952 年 3 月 30 日父王去世即继位（10 月 27 日加冕）")
a("Q189710", "Sultan of Selangor", "Sharafuddin of Selangor", D(2001, 11, 22), None, "2001 年 11 月 22 日继位（2003 年 3 月 8 日加冕）")
a("Q34", "Monarch of Sweden", "Charles VIII of Sweden", D(1467, 11, 12), D(1470, 5, 15), "第三次在位")
a("Q282428", "Sultan of Egypt", "Q327441", D(1250, 7, 31), D(1257, 4, 10), "艾伯克 1250 年 7 月 31 日即苏丹位（1250–1254 年与阿尤布家族的阿什拉夫·穆萨名义共治），1257 年 4 月 10 日被杀", W + "Aybak")
a("Q12536", "Caliph", "Al-Mu'tazz", D(866, 1, 25), D(869, 7, 13), "穆斯塔因 866 年 1 月 25 日退位后为唯一哈里发")
a("Q104863335", "King of Poland", "Mieszko II Lambert", D(1025, 6, 17), D(1031), "1025 年 6 月 17 日父王去世即继位（12 月 25 日加冕）")
