"""把有再分发许可的欧洲历史一级行政区收成一份几何。

原始文件只在构建机的 /tmp/euadm，不进仓库。
没有合法几何的国家不在这里补，也不用今天的省界顶上。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import unicodedata
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pyogrio
from pyproj import Transformer
from shapely import wkb
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
RAW = Path("/tmp/euadm")
OUT = ROOT / "data" / "curated" / "geom" / "europe_admin.geojson"

# 点名核对。构建结束时打印，不写进几何。
CHECKS = [
    ("1910-06-01", 16.3738, 48.2082, "下奥地利"),
    ("1910-06-01", 14.421, 50.087, "波希米亚"),
    ("1914-06-01", 20.51, 54.71, "东普鲁士"),
    ("1850-06-01", 11.575, 48.137, "巴伐利亚"),
    ("1922-06-01", 2.3522, 48.8566, "塞纳"),
    ("1870-06-01", 6.175, 49.119, "摩泽尔"),
    ("1872-06-01", 6.175, 49.119, None),
    ("1860-06-01", 2.3522, 48.8566, None),
    ("1897-07-01", 37.6173, 55.7558, "莫斯科"),
    ("1926-07-01", 37.6173, 55.7558, "莫斯科"),
    ("1934-06-01", 21.012, 52.23, "华沙"),
    ("1922-06-01", 21.012, 52.23, "华沙"),
    ("1936-06-01", 12.496, 41.903, "罗马"),
    ("1862-07-01", 12.496, 41.903, None),
    ("1850-06-01", -0.128, 51.507, "米德尔塞克斯"),
    ("1900-06-01", -0.128, 51.507, None),
    ("1900-06-01", -3.703, 40.417, None),
    ("1930-06-01", 26.102, 44.426, None),
    ("1930-06-01", 20.457, 44.817, None),
]


def next_day(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return (date(y, m, d) + timedelta(days=1)).isoformat()


def norm_key(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.replace("’", "'").replace("–", "-").upper().split())


def zh_lookup(table: dict, text: str) -> str | None:
    if text in table:
        return table[text]
    key = norm_key(text)
    for src, zh in table.items():
        if norm_key(src) == key:
            return zh
    return None


FR = {
    "SEINE": "塞纳", "SEINE-ET-OISE": "塞纳-瓦兹", "SEINE-ET-MARNE": "塞纳-马恩",
    "SEINE-INFERIEURE": "下塞纳", "LOIRE-INFERIEURE": "下卢瓦尔", "CHARENTE-INFERIEURE": "下夏朗德",
    "BASSES-ALPES": "下阿尔卑斯", "BASSES-PYRENEES": "下比利牛斯", "HAUTES-ALPES": "上阿尔卑斯",
    "HAUTES-PYRENEES": "上比利牛斯", "HAUTE-VIENNE": "上维埃纳", "HAUTE-LOIRE": "上卢瓦尔",
    "HAUTE-GARONNE": "上加龙", "HAUTE-MARNE": "上马恩", "HAUTE-SAONE": "上索恩", "HAUTE-SAVOIE": "上萨瓦",
    "COTES-DU-NORD": "北滨海", "COTE-D'OR": "科多尔", "MEURTHE-ET-MOSELLE": "默尔特-摩泽尔",
    "TERRITOIRE-DE-BELFORT": "贝尔福地区", "BAS-RHIN": "下莱茵", "HAUT-RHIN": "上莱茵", "MOSELLE": "摩泽尔",
    "CORSE": "科西嘉", "NORD": "诺尔", "RHONE": "罗讷", "VAR": "瓦尔", "AIN": "安", "AISNE": "埃纳",
    "ALLIER": "阿列", "ARDECHE": "阿尔代什", "ARDENNES": "阿登", "ARIEGE": "阿列日", "AUBE": "奥布",
    "AUDE": "奥德", "AVEYRON": "阿韦龙", "BOUCHES-DU-RHONE": "罗讷河口", "CALVADOS": "卡尔瓦多斯",
    "CANTAL": "康塔尔", "CHARENTE": "夏朗德", "CHER": "谢尔", "CORREZE": "科雷兹", "CREUSE": "克勒兹",
    "DEUX-SEVRES": "德塞夫勒", "DORDOGNE": "多尔多涅", "DOUBS": "杜", "DROME": "德龙", "EURE": "厄尔",
    "EURE-ET-LOIR": "厄尔-卢瓦尔", "FINISTERE": "菲尼斯泰尔", "GARD": "加尔", "GERS": "热尔",
    "GIRONDE": "吉伦特", "HERAULT": "埃罗", "ILLE-ET-VILAINE": "伊勒-维莱讷", "INDRE": "安德尔",
    "INDRE-ET-LOIRE": "安德尔-卢瓦尔", "ISERE": "伊泽尔", "JURA": "汝拉", "LANDES": "朗德",
    "LOIR-ET-CHER": "卢瓦尔-谢尔", "LOIRE": "卢瓦尔", "LOIRET": "卢瓦雷", "LOT": "洛特",
    "LOT-ET-GARONNE": "洛特-加龙", "LOZERE": "洛泽尔", "MAINE-ET-LOIRE": "曼恩-卢瓦尔", "MANCHE": "芒什",
    "MARNE": "马恩", "MAYENNE": "马耶讷", "MEUSE": "默兹", "MORBIHAN": "莫尔比昂", "NIEVRE": "涅夫勒",
    "OISE": "瓦兹", "ORNE": "奥恩", "PAS-DE-CALAIS": "加来海峡", "PUY-DE-DOME": "多姆山",
    "PYRENEES-ORIENTALES": "东比利牛斯", "SAONE-ET-LOIRE": "索恩-卢瓦尔", "SARTHE": "萨尔特",
    "SAVOIE": "萨瓦", "SEINE-MARITIME": "滨海塞纳", "SOMME": "索姆", "TARN": "塔恩",
    "TARN-ET-GARONNE": "塔恩-加龙", "VAR": "瓦尔", "VAUCLUSE": "沃克吕兹", "VENDEE": "旺代",
    "VIENNE": "维埃纳", "VOSGES": "孚日", "YONNE": "约讷", "ALPES-MARITIMES": "滨海阿尔卑斯",
    "MEURTHE": "默尔特", "RHONE-ET-LOIRE": "罗讷-卢瓦尔",
}

DE = {
    "Erzherzogtum Österreich ob der Enns": "上奥地利",
    "Erzherzogtum Österreich unter der Enns": "下奥地利",
    "Freie Stadt Krakau": "克拉科夫自由市",
    "Gefürstete Grafschaft Tirol mit dem Lande Vorarlberg": "蒂罗尔与福拉尔贝格",
    "Großfürstentum Siebenbürgen": "特兰西瓦尼亚",
    "Herzogtum Schlesien": "西里西亚公国",
    "Herzogtum Steiermark": "施蒂利亚",
    "Königreich Böhmen": "波希米亚",
    "Königreich Dalmatien": "达尔马提亚",
    "Königreich Galizien und Lodomerien": "加利西亚和洛多梅里亚",
    "Königreich Illyrien": "伊利里亚",
    "Königreich Kroatien": "克罗地亚",
    "Königreich Lombardo-Venetien": "伦巴第-威尼西亚",
    "Königreich Slawonien": "斯拉沃尼亚",
    "Königreich Ungarn": "匈牙利",
    "Markgrafschaft Mähren": "摩拉维亚",
    "Militärgrenze": "军政边境",
    "Königreich Kroatien und Slawonien": "克罗地亚-斯拉沃尼亚",
    "Herzogtum Bukowina": "布科维纳",
    "Herzogtum Krain": "卡尼奥拉",
    "Herzogtum Kärnten": "卡林西亚",
    "Herzogtum Salzburg": "萨尔茨堡",
    "Königreich Lombardei": "伦巴第",
    "Königreich Venetien": "威尼西亚",
    "Küstenland": "滨海地区",
    "Woiwodschaft Serbien und Temeser Banat": "塞尔维亚与泰梅什巴纳特",
    "Gefürstete Grafschaft Görz und Gradisca": "戈里齐亚-格拉迪斯卡",
    "Gefürstete Grafschaft Tirol": "蒂罗尔",
    "Land Vorarlberg": "福拉尔贝格",
    "Markgrafschaft Istrien": "伊斯特拉",
    "Triest mit Gebiet": "的里雅斯特",
    "Königreich Kroatien und Salawonien": "克罗地亚-斯拉沃尼亚",
    "Bosnien-Herzegowina": "波斯尼亚-黑塞哥维那",
    "Freie Stadt Fiume mit Gebiet": "阜姆",
    "Markgraftschaft Istrien": "伊斯特拉",
    "Markgraftschaft Mähren": "摩拉维亚",
    "Brandenburg": "勃兰登堡", "Preußen": "普鲁士", "Schleswig-Holstein": "石勒苏益格-荷尔斯泰因",
    "Berlin": "柏林", "Hannover": "汉诺威", "Hessen-Nassau": "黑森-拿骚", "Hohenzollern": "霍亨索伦",
    "Ostpreußen": "东普鲁士", "Pommern": "波美拉尼亚", "Posen": "波森", "Rheinprovinz": "莱茵省",
    "Sachsen": "萨克森", "Schlesien": "西里西亚", "Westfalen": "威斯特法伦", "Westpreußen": "西普鲁士",
    "Anhalt-Bernburg": "安哈尔特-贝恩堡", "Anhalt-Dessau": "安哈尔特-德绍", "Anhalt-Köthen": "安哈尔特-克滕",
    "Bayern": "巴伐利亚", "Bergedorf": "贝格多夫", "Braunschweig": "不伦瑞克", "Bremen": "不来梅",
    "Frankfurt": "法兰克福", "Hamburg": "汉堡", "Hessen-Darmstadt": "黑森-达姆施塔特",
    "Hessen-Homburg": "黑森-洪堡", "Hessen-Kassel": "黑森-卡塞尔",
    "Hohenzollern-Hechingen": "霍亨索伦-黑兴根", "Hohenzollern-Sigmaringen": "霍亨索伦-锡格马林根",
    "Holstein": "荷尔斯泰因", "Lauenburg": "劳恩堡", "Lippe-Detmold": "利珀-代特莫尔德",
    "Lübeck": "吕贝克", "Mecklenburg-Schwerin": "梅克伦堡-什未林", "Mecklenburg-Strelitz": "梅克伦堡-施特雷利茨",
    "Nassau": "拿骚", "Oldenburg": "奥尔登堡",
    "Reuß jüngere Linie (Lobenstein, Ebersdorf, Gera, Schleiz)": "罗伊斯幼支",
    "Reuß ältere Linie (Reuß-Greiz)": "罗伊斯长支",
    "Sachsen-Coburg-Saalfeld": "萨克森-科堡-萨尔费尔德", "Sachsen-Gotha-Altenburg": "萨克森-哥达-阿尔滕堡",
    "Sachsen-Hildburghausen": "萨克森-希尔德布格豪森", "Sachsen-Meiningen": "萨克森-迈宁根",
    "Sachsen-Weimar-Eisenach": "萨克森-魏玛-艾森纳赫", "Schaumburg-Lippe": "绍姆堡-利珀",
    "Schleswig": "石勒苏益格", "Schwarzburg-Rudolstadt": "施瓦茨堡-鲁多尔施塔特",
    "Schwarzburg-Sondershausen": "施瓦茨堡-松德斯豪森", "Waldeck": "瓦尔德克",
    "Sachsen-Coburg und Gotha": "萨克森-科堡-哥达", "Anhalt-Dessau-Köthen": "安哈尔特-德绍-克滕",
    "Anhalt": "安哈尔特", "Sachsen-Altenburg": "萨克森-阿尔滕堡",
    "Jülich-Kleve-Berg": "于利希-克莱沃-贝格", "Niederrhein": "下莱茵",
    "Oberhessen": "上黑森", "Rheinhessen": "莱茵黑森", "Starkenburg": "施塔肯堡",
}

KIND = {
    "Provinz": "省", "Provinz mit eingeschränkten Befugnissen": "省",
    "Königreich": "王国", "Herzogtum": "公国", "Herztogtum": "公国", "crownland": "王冠领地",
    "Fürstentum": "侯国", "Großherzogtum": "大公国", "Freie Stadt": "自由市",
    "Erzherzogtum": "大公国", "Markgrafschaft": "藩侯国", "Markgraftschaft": "藩侯国",
    "Militärgrenze": "军政边境", "military frontier": "军政边境",
    "Gefürstete Grafschaft": "伯国", "Kommissionsbezirk der Provinzstadt": "省",
    "Land": "领地", "Kurfürstentum": "选侯国", "Kondominium": "共管", "Protektorat": "保护领",
    "Woiwodschaft": "省", "Großfürstentum": "大公国", "Reichsunmittelbare Stadt": "帝国城市",
    "-": "王冠领地",
}

IT = {
    "Torino": "都灵", "Vercelli": "韦尔切利", "Novara": "诺瓦拉", "Cuneo": "库内奥",
    "Alessandria": "亚历山德里亚", "Valle d'Aosta": "瓦莱达奥斯塔", "Imperia": "因佩里亚",
    "Savona": "萨沃纳", "Genova": "热那亚", "La Spezia": "拉斯佩齐亚", "Varese": "瓦雷泽",
    "Como": "科莫", "Sondrio": "松德里奥", "Milano": "米兰", "Bergamo": "贝加莫",
    "Brescia": "布雷西亚", "Pavia": "帕维亚", "Cremona": "克雷莫纳", "Mantova": "曼托瓦",
    "Bolzano - Bozen": "博尔扎诺", "Trento": "特伦托", "Verona": "维罗纳", "Vicenza": "维琴察",
    "Belluno": "贝卢诺", "Treviso": "特雷维索", "Venezia": "威尼斯", "Padova": "帕多瓦",
    "Rovigo": "罗维戈", "Provincia del Friuli": "弗留利", "Gorizia": "戈里齐亚", "Trieste": "的里雅斯特",
    "Piacenza": "皮亚琴察", "Parma": "帕尔马", "Reggio nell'Emilia": "雷焦艾米利亚", "Modena": "摩德纳",
    "Bologna": "博洛尼亚", "Ferrara": "费拉拉", "Ravenna": "拉文纳", "Forli'": "弗利", "Forlì": "弗利",
    "Pesaro Urbino": "佩萨罗-乌尔比诺", "Ancona": "安科纳", "Macerata": "马切拉塔",
    "Ascoli Piceno": "阿斯科利皮切诺", "Massa e Carrara": "马萨-卡拉拉", "Lucca": "卢卡",
    "Pistoia": "皮斯托亚", "Firenze": "佛罗伦萨", "Livorno": "里窝那", "Pisa": "比萨",
    "Arezzo": "阿雷佐", "Siena": "锡耶纳", "Grosseto": "格罗塞托", "Perugia": "佩鲁贾",
    "Terni": "特尔尼", "Viterbo": "维泰博", "Rieti": "列蒂", "Roma": "罗马", "Frosinone": "弗罗西诺内",
    "Benevento": "贝内文托", "Napoli": "那不勒斯", "Avellino": "阿韦利诺", "Salerno": "萨莱诺",
    "Aquila degli Abruzzi": "拉奎拉", "Teramo": "泰拉莫", "Pescara": "佩斯卡拉", "Chieti": "基耶蒂",
    "Campobasso": "坎波巴索", "Foggia": "福贾", "Bari delle Puglie": "巴里", "Ionio": "伊奥尼亚",
    "Brindisi": "布林迪西", "Lecce": "莱切", "Potenza": "波坦察", "Matera": "马泰拉",
    "Cosenza": "科森扎", "Catanzaro": "卡坦扎罗", "Reggio di Calabria": "雷焦卡拉布里亚",
    "Trapani": "特拉帕尼", "Palermo": "巴勒莫", "Messina": "墨西拿", "Agrigento": "阿格里真托",
    "Caltanissetta": "卡尔塔尼塞塔", "Enna": "恩纳", "Catania": "卡塔尼亚", "Ragusa": "拉古萨",
    "Siracusa": "锡拉库萨", "Sassari": "萨萨里", "Nuoro": "努奥罗", "Cagliari": "卡利亚里",
    "Udine": "乌迪内", "Taranto": "塔兰托", "L'Aquila": "拉奎拉", "Bari": "巴里",
    "Abruzzo Citeriore": "近阿布鲁佐", "Abruzzo Ulteriore I": "远阿布鲁佐第一",
    "Abruzzo Ulteriore II": "远阿布鲁佐第二", "Aosta": "奥斯塔", "Asti": "阿斯蒂",
    "Basilicata": "巴西利卡塔", "Bolzano/Bozen": "博尔扎诺",
    "Calabria Citeriore": "近卡拉布里亚", "Calabria Ulteriore I": "远卡拉布里亚第一",
    "Calabria Ulteriore II": "远卡拉布里亚第二", "Capitanata": "卡皮塔纳塔", "Caserta": "卡塞塔",
    "Friuli": "弗留利", "Girgenti": "吉尔真蒂", "Isernia": "伊塞尔尼亚", "Jonio": "伊奥尼亚",
    "Latina": "拉蒂纳", "Massa-Carrara": "马萨-卡拉拉", "Molise": "莫利塞", "Noto": "诺托",
    "Oristano": "奥里斯塔诺", "Pesaro e Urbino": "佩萨罗-乌尔比诺", "Pordenone": "波代诺内",
    "Porto Maurizio": "波尔托毛里齐奥", "Principato Citeriore": "近普林奇帕托",
    "Principato Ulteriore": "远普林奇帕托", "Spezia": "斯佩齐亚",
    "Terra d'Otranto": "奥特朗托之地", "Terra del Lavoro": "拉沃罗之地", "Terra di Bari": "巴里之地",
    "Umbria": "翁布里亚", "Venezia Giulia": "威尼斯朱利亚", "Venezia Tridentina": "威尼斯特伦蒂纳",
}

PL = {
    "Białystok": "比亚韦斯托克", "Kielce": "凯尔采", "Kraków": "克拉科夫", "Lublin": "卢布林",
    "Lwów": "利沃夫", "Nowogródek": "新格鲁代克", "Polesie": "波莱谢", "Pomorze": "波美拉尼亚",
    "Poznań": "波兹南", "Stanisławów": "斯坦尼斯瓦武夫", "Tarnopol": "捷尔诺波尔",
    "Warszawa": "华沙", "Warszawa Capitol": "华沙市", "Wilno": "维尔纽斯", "Wołyń": "沃伦",
    "Łódź": "罗兹", "Śląsk": "西里西亚",
}

UK = {
    "Aberdeenshire": "阿伯丁", "Anglesey": "安格尔西", "Angus": "安格斯", "Antrim": "安特里姆",
    "Argyllshire": "阿盖尔", "Armagh": "阿马", "Ayrshire": "艾尔", "Banffshire": "班夫",
    "Bedfordshire": "贝德福德", "Berkshire": "伯克", "Berwickshire": "贝里克",
    "Brecknockshire": "布雷克诺克", "Buckinghamshire": "白金汉", "Buteshire": "比特",
    "Caernarfonshire": "卡那封", "Caithness": "凯斯内斯", "Cambridgeshire": "剑桥",
    "Cardiganshire": "卡迪根", "Carmarthenshire": "卡马森", "Cheshire": "柴郡",
    "Clackmannanshire": "克拉克曼南", "Cornwall": "康沃尔", "Cromartyshire": "克罗默蒂",
    "Cumberland": "坎伯兰", "Denbighshire": "登比", "Derbyshire": "德比", "Devon": "德文",
    "Dorset": "多塞特", "Down": "唐", "Dumfriesshire": "邓弗里斯", "Dunbartonshire": "邓巴顿",
    "Durham": "达勒姆", "East Lothian": "东洛锡安", "Essex": "埃塞克斯", "Fermanagh": "弗马纳",
    "Fife": "法夫", "Flintshire": "弗林特", "Glamorgan": "格拉摩根", "Gloucestershire": "格洛斯特",
    "Hampshire": "汉普", "Herefordshire": "赫里福德", "Hertfordshire": "赫特福德",
    "Huntingdonshire": "亨廷登", "Inverness-shire": "因弗内斯", "Kent": "肯特",
    "Kincardineshire": "金卡丁", "Kinross-shire": "金罗斯", "Kirkcudbrightshire": "柯库布里",
    "Lanarkshire": "拉纳克", "Lancashire": "兰开夏", "Leicestershire": "莱斯特",
    "Lincolnshire": "林肯", "Londonderry": "伦敦德里", "Merionethshire": "梅里奥尼思",
    "Middlesex": "米德尔塞克斯", "Midlothian": "中洛锡安", "Monmouthshire": "蒙茅斯",
    "Montgomeryshire": "蒙哥马利", "Morayshire": "马里", "Nairnshire": "奈恩", "Norfolk": "诺福克",
    "Northamptonshire": "北安普顿", "Northumberland": "诺森伯兰", "Nottinghamshire": "诺丁汉",
    "Orkney": "奥克尼", "Oxfordshire": "牛津", "Peeblesshire": "皮布尔斯", "Pembrokeshire": "彭布罗克",
    "Perthshire": "珀斯", "Radnorshire": "拉德诺", "Renfrewshire": "伦弗鲁", "Ross-shire": "罗斯",
    "Roxburghshire": "罗克斯堡", "Rutland": "拉特兰", "Selkirkshire": "塞尔扣克", "Shetland": "设得兰",
    "Shropshire": "什罗普", "Somerset": "萨默塞特", "Staffordshire": "斯塔福德",
    "Stirlingshire": "斯特灵", "Suffolk": "萨福克", "Surrey": "萨里", "Sussex": "萨塞克斯",
    "Sutherland": "萨瑟兰", "Tyrone": "蒂龙", "Warwickshire": "沃里克", "West Lothian": "西洛锡安",
    "Westmorland": "威斯特摩兰", "Wigtownshire": "威格敦", "Wiltshire": "威尔特",
    "Worcestershire": "伍斯特", "Yorkshire": "约克",
}

RU = {
    "Abosskaya guberniya": "奥布省", "Akmolinskaya oblast": "阿克莫林斯克州",
    "Amurskaya oblast": "阿穆尔州", "Arkhangelskaya guberniya": "阿尔汉格尔斯克省",
    "Astrakhanskaya guberniya": "阿斯特拉罕省", "Bakinskaya guberniya": "巴库省",
    "Bessarabskaya guberniya": "比萨拉比亚省", "Bukhara emirate": "布哈拉埃米尔国",
    "Chernigovskaya guberniya": "切尔尼戈夫省", "Chernomorskaya guberniya": "黑海省",
    "Dagestanskaya oblast": "达吉斯坦州", "Ekaterinoslavskaya guberniya": "叶卡捷琳诺斯拉夫省",
    "Elisavetpolskaya guberniya": "伊丽莎白波尔省", "Eniseyskaya guberniya": "叶尼塞省",
    "Erivanskaya guberniya": "埃里温省", "Estlyandskaya guberniya": "爱斯特兰省",
    "Ferganskaya oblast": "费尔干纳州", "Grodnenskaya guberniya": "格罗德诺省",
    "Irkutskaya oblast": "伊尔库茨克州", "Kalishskaya guberniya": "卡利什省",
    "Kaluzhskaya guberniya": "卡卢加省", "Karsskaya oblast": "卡尔斯州",
    "Kazanskaya guberniya": "喀山省", "Keletskaya guberniya": "凯尔采省",
    "Kharkovskaya guberniya": "哈尔科夫省", "Khersonskaya guberniya": "赫尔松省",
    "Khiva khanate": "希瓦汗国", "Kiyevskaya guberniya": "基辅省",
    "Kostromskaya guberniya": "科斯特罗马省", "Kovenskaya guberniya": "科夫诺省",
    "Kubanskaya oblast": "库班州", "Kuopioskaya guberniya": "库奥皮奥省",
    "Kurlyandskaya guberniya": "库尔兰省", "Kurskaya guberniya": "库尔斯克省",
    "Kutaisskaya guberniya": "库塔伊西省", "Liflyandskaya guberniya": "利夫兰省",
    "Lomzhinskaya guberniya": "沃姆扎省", "Lyublinskaya guberniya": "卢布林省",
    "Minskaya guberniya": "明斯克省", "Mogilevskaya guberniya": "莫吉廖夫省",
    "Moskovskaya guberniya": "莫斯科省", "Nizhegorodskaya guberniya": "下诺夫哥罗德省",
    "Novgorodskaya guberniya": "诺夫哥罗德省", "Nyulandskaya guberniya": "新地省",
    "Olonetskaya guberniya": "奥洛涅茨省", "Orenburgskaya guberniya": "奥伦堡省",
    "Orlovskaya guberniya": "奥廖尔省", "Penzenskaya guberniya": "奔萨省",
    "Permskaya guberniya": "彼尔姆省", "Peterburgskaya guberniya": "圣彼得堡省",
    "Petrokovskaya guberniya": "彼得库夫省", "Plotskaya guberniya": "普沃茨克省",
    "Podolskaya guberniya": "波多利亚省", "Poltavskaya guberniya": "波尔塔瓦省",
    "Primorskaya oblast": "滨海州", "Pskovskaya guberniya": "普斯科夫省",
    "Radomskaya guberniya": "拉多姆省", "Ryazanskaya guberniya": "梁赞省",
    "Sakhalin": "萨哈林", "Samarkandskaya oblast": "撒马尔罕州",
    "Samarskaya guberniya": "萨马拉省", "Sankt-Mikhelskaya guberniya": "圣米歇尔省",
    "Saratovskaya guberniya": "萨拉托夫省", "Sedletskaya guberniya": "谢德尔采省",
    "Semipalatinskaya oblast": "塞米巴拉金斯克州", "Semirechenskaya oblast": "七河州",
    "Simbirskaya guberniya": "辛比尔斯克省", "Smolenskaya guberniya": "斯摩棱斯克省",
    "Stravropolskaya oblast": "斯塔夫罗波尔州", "Suvalkskaya guberniya": "苏瓦乌基省",
    "Syr-Daryinskaya oblast": "锡尔河州", "Tambovskaya guberniya": "坦波夫省",
    "Tavastgusskaya guberniya": "海梅省", "Tavricheskaya guberniya": "塔夫利达省",
    "Terskaya oblast": "捷列克州", "Tiflisskaya guberniya": "第比利斯省",
    "Tobolskaya guberniya": "托博尔斯克省", "Tomskaya guberniya": "托木斯克省",
    "Tulskaya guberniya": "图拉省", "Turgayskaya oblast": "图尔盖州",
    "Tverskaya guberniya": "特维尔省", "Ufimskaya guberniya": "乌法省",
    "Uleaborgskaya guberniya": "奥卢省", "Uralskaya oblast": "乌拉尔斯克州",
    "Varshavskaya guberniya": "华沙省", "Vazaskaya guberniya": "瓦萨省",
    "Vilenskaya guberniya": "维尔纳省", "Vitebskaya guberniya": "维捷布斯克省",
    "Vladimirskaya guberniya": "弗拉基米尔省", "Vologodskaya guberniya": "沃洛格达省",
    "Volynskaya guberniya": "沃伦省", "Voronezhskaya guberniya": "沃罗涅日省",
    "Voyska Donskogo oblast": "顿河军州", "Vyatskaya guberniya": "维亚特卡省",
    "Vyborgskaya guberniya": "维堡省", "Yakutskaya oblast": "雅库茨克州",
    "Yaroslavskaya guberniya": "雅罗斯拉夫尔省", "Zabaykalskaya oblast": "外贝加尔州",
    "Zakaspyskaya oblast": "外里海州",
}

SU = {
    "AC Grozny": "格罗兹尼自治区", "AC Vladikavkaz": "弗拉季高加索自治区",
    "Adygei-Cherkess AR": "阿迪格-切尔克斯自治州", "Arkhangelsk province": "阿尔汉格尔斯克省",
    "Astrakhan province": "阿斯特拉罕省", "Bashkir ASSR": "巴什基尔自治共和国",
    "Belorussian ASSR": "白俄罗斯自治共和国", "Bryansk province": "布良斯克省",
    "Buryat-Mongol ASSR": "布里亚特-蒙古自治共和国", "Chechen AR": "车臣自治州",
    "Cherepovets province": "切列波韦茨省", "Cherkess AR": "切尔克斯自治州",
    "Chuvash ASSR": "楚瓦什自治共和国", "Crimean ASSR": "克里米亚自治共和国",
    "Dagestan ASSR": "达吉斯坦自治共和国", "Far East region": "远东边疆区",
    "Ingush AR": "印古什自治州", "Ivanovo-Voznesensk province": "伊万诺沃-沃兹涅先斯克省",
    "Kabardino-Balkar AR": "卡巴尔达-巴尔卡尔自治州", "Kalmyk AR": "卡尔梅克自治州",
    "Kaluga province": "卡卢加省", "Karachai AR": "卡拉恰伊自治州", "Karakalpak AR": "卡拉卡尔帕克自治州",
    "Karelian ASSR": "卡累利阿自治共和国", "Kazakh ASSR": "哈萨克自治共和国",
    "Kirghiz ASSR": "吉尔吉斯自治共和国", "Komi (Zyryanskaya) AR": "科米自治州",
    "Kostroma province": "科斯特罗马省", "Kursk province": "库尔斯克省",
    "Leningrad province": "列宁格勒省", "Mariyskaya AR": "马里自治州", "Moscow province": "莫斯科省",
    "Murmansk province": "摩尔曼斯克省", "Nizhny Novgorod province": "下诺夫哥罗德省",
    "North Osetian AR": "北奥塞梯自治州", "North-Caucasus region": "北高加索边疆区",
    "Northern Dvina province": "北德维纳省", "Novgorod province": "诺夫哥罗德省",
    "Oirat AR": "卫拉特自治州", "Orel province": "奥廖尔省", "Orenburg province": "奥伦堡省",
    "Penza province": "奔萨省", "Pskov province": "普斯科夫省", "Ryazan province": "梁赞省",
    "Samara province": "萨马拉省", "Saratov province": "萨拉托夫省", "Siberian region": "西伯利亚边疆区",
    "Smolensk province": "斯摩棱斯克省", "Stalingrad province": "斯大林格勒省",
    "Tambov province": "坦波夫省", "Tatar ASSR": "鞑靼自治共和国",
    "Transcaucasian SFSR": "外高加索联邦", "Tula province": "图拉省", "Turkmen SSR": "土库曼共和国",
    "Tver province": "特维尔省", "Ukrainian ASSR": "乌克兰共和国", "Ulyanovsk province": "乌里扬诺夫斯克省",
    "Ural region": "乌拉尔州", "Uzbek SSR": "乌兹别克共和国", "Vladimir province": "弗拉基米尔省",
    "Volga German ASSR": "伏尔加德意志自治共和国", "Vologda province": "沃洛格达省",
    "Voronezh province": "沃罗涅日省", "Votskaya AR": "沃特自治州", "Vyatka province": "维亚特卡省",
    "Yakut ASSR": "雅库特自治共和国", "Yaroslavl province": "雅罗斯拉夫尔省",
}


def clean_geom(geom, tol: float):
    if geom is None or geom.is_empty:
        return None
    geom = make_valid(geom)
    if geom.geom_type == "GeometryCollection":
        parts = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        geom = unary_union(parts) if parts else None
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        return None
    # 越过 180° 的经度收回来。整块都在 180° 以东时才平移，避免把横跨日界线的环拉成一条横贯地图的带子。
    minx, miny, maxx, maxy = geom.bounds
    if minx > 180:
        geom = transform(lambda x, y: (x - 360.0, y), geom)
    geom = geom.simplify(tol, preserve_topology=True)
    if geom.is_empty or geom.area < 1e-6:
        return None
    return geom


def dump_geom(geom) -> dict:
    def rec(node):
        if isinstance(node, (list, tuple)) and node and isinstance(node[0], (int, float)):
            return [round(float(node[0]), 4), round(float(node[1]), 4)]
        return [rec(part) for part in node]

    raw = mapping(geom)
    raw["coordinates"] = rec(raw["coordinates"])
    return raw


def geom_hash(geom) -> str:
    return hashlib.sha1(json.dumps(dump_geom(geom), separators=(",", ":")).encode()).hexdigest()


def read_wkb_layer(path, columns, layer=None, encoding=None):
    kwargs = {"columns": columns}
    if layer:
        kwargs["layer"] = layer
    if encoding:
        kwargs["encoding"] = encoding
    _meta, table = pyogrio.read_arrow(path, **kwargs)
    info = pyogrio.read_info(path, layer=layer) if layer else pyogrio.read_info(path)
    names = table.column(columns[0]).to_pylist()
    blobs = table.column("wkb_geometry").to_pylist()
    extra = {}
    for col in columns[1:]:
        extra[col] = table.column(col).to_pylist()
    return info.get("crs"), names, blobs, extra


def reproject(blob, crs):
    geom = wkb.loads(bytes(blob))
    if crs and "4326" not in str(crs):
        target = "EPSG:2154" if "Lambert" in str(crs) else crs
        transformer = Transformer.from_crs(target, "EPSG:4326", always_xy=True)
        geom = transform(transformer.transform, geom)
    return geom


def add(rows, *, name_src, name_zh, kind, nominal, start, end, source_id, license_name, url, precision, geom, tol):
    geom = clean_geom(geom, tol)
    if geom is None or not start or not end:
        return
    rows.append({
        "name_src": name_src,
        "name": name_zh or name_src,
        "kind": kind,
        "nominal": nominal,
        "from": start,
        "until": end,
        "source_id": source_id,
        "license": license_name,
        "url": url,
        "precision": precision,
        "geom": geom,
    })


def load_histogis(rows):
    zpath = RAW / "histogis-v3.zip"
    skip_src = ("Europe ",)
    skip_name = {"Deutsches Kaiserreich", "Norddeutscher Bund", "Kaisertum Österreich", "xmasland"}
    url = "https://doi.org/10.5281/zenodo.2650712"
    note = (
        "HistoGIS v3，CC BY 4.0。原文件说明几何取自 Census Mosaic、属性取自 HGIS Germany。"
        "这里按 HistoGIS 公布的 CC BY 4.0 收录，没有另用 MPIDR 的非商业包。"
        "日期用原文件的起止日，结束日的次日起不再画。不是当日测绘。"
    )
    with zipfile.ZipFile(zpath) as zf:
        for name in zf.namelist():
            if "/single_files/" not in name or not name.endswith(".geojson"):
                continue
            feat = json.loads(zf.read(name))
            prop = feat.get("properties") or {}
            src = prop.get("source_name") or ""
            if src.startswith(skip_src) or prop.get("name") in skip_name:
                continue
            start, end = prop.get("start_date"), prop.get("end_date")
            if not start or not end:
                continue
            nominal = "奥匈帝国" if "Austro-Hungarian" in src or (start >= "1867-12-22" and "Crownland" in src) else ""
            if "Crownland" in src and start < "1867-12-22":
                nominal = "奥地利帝国"
            elif "Prussia Provinces" in src or "German Empire Provinces" in src:
                nominal = "普鲁士"
            elif "Hesse-Darmstadt" in src:
                nominal = "黑森-达姆施塔特"
            elif src.startswith("German States"):
                nominal = "德意志各邦"
            label = prop.get("name") or ""
            # 同名的王国和省要分开。普鲁士省不是普鲁士王国。
            zh = zh_lookup(DE, label)
            if label == "Preußen" and prop.get("adm_name") == "Königreich":
                zh = "普鲁士王国"
            elif label == "Preußen":
                zh = "普鲁士省"
            elif label == "Sachsen" and "Provinz" in (prop.get("adm_name") or ""):
                zh = "萨克森省"
            elif label == "Sachsen":
                zh = "萨克森王国"
            elif label == "Hannover" and prop.get("adm_name") == "Königreich":
                zh = "汉诺威王国"
            add(
                rows, name_src=label, name_zh=zh, kind=KIND.get(prop.get("adm_name") or "", "行政区"),
                nominal=nominal or "—", start=start, end=next_day(end),
                source_id="histogis", license_name="CC BY 4.0", url=url, precision=note,
                geom=shape(feat["geometry"]), tol=0.02,
            )


def load_france(rows):
    note = (
        "Victor Gay，TRF-GIS 省多边形，CC BY 4.0，doi:10.7910/DVN/ULQYM5。"
        "这是第三共和国的法定省，不是占领区。"
        "年档相同的几何连成一段。1871年5月10日《法兰克福条约》前后几何不同的省，从这一天切开。"
        "1918年11月的收回没有切进1918年档，1919年档从1月1日起。1791年至1869年、1941年以后没有这套几何。"
    )
    url = "https://doi.org/10.7910/DVN/ULQYM5"
    by_name: dict[str, dict[int, tuple]] = {}
    folder = RAW / "trf" / "poly"
    for zpath in sorted(folder.glob("DEPARTEMENTS_*.zip")):
        year = int(zpath.stem.rsplit("_", 1)[-1])
        dest = folder / str(year)
        if not any(dest.glob("*.shp")):
            zipfile.ZipFile(zpath).extractall(dest)
        shp = next(dest.glob("*.shp"))
        crs, names, blobs, extra = read_wkb_layer(shp, ["dep_name", "dep_id"])
        for label, blob, dep_id in zip(names, blobs, extra["dep_id"]):
            geom = clean_geom(reproject(blob, crs), 0.015)
            if geom is None:
                continue
            by_name.setdefault(label, {})[year] = (geom_hash(geom), geom, dep_id)
    for label, years in by_name.items():
        ordered = sorted(years)
        span = None
        for year in ordered:
            digest, geom, dep_id = years[year]
            if span and digest == span["hash"] and year == span["last"] + 1:
                span["last"] = year
                continue
            if span:
                _flush_france(rows, label, span, note, url)
            span = {"hash": digest, "geom": geom, "dep_id": dep_id, "first": year, "last": year}
        if span:
            _flush_france(rows, label, span, note, url)


def _flush_france(rows, label, span, note, url):
    start = f"{span['first']:04d}-01-01"
    end = f"{span['last'] + 1:04d}-01-01"
    if span["first"] == 1871:
        start = "1871-05-10"
    if span["last"] == 1870:
        end = "1871-05-10"
    zh = zh_lookup(FR, label.replace(" ", "-"))
    rows.append({
        "name_src": label, "name": zh or label, "kind": "省", "nominal": "法国",
        "from": start, "until": end, "source_id": "trf-gis", "license": "CC BY 4.0",
        "url": url, "precision": note, "geom": span["geom"],
    })


def load_italy(rows):
    snaps = [
        (1861, "1861-03-17"), (1871, "1871-12-31"), (1881, "1881-12-31"),
        (1901, "1901-02-10"), (1911, "1911-06-10"), (1921, "1921-12-01"),
        (1923, "1923-12-31"), (1925, "1925-12-31"), (1927, "1927-12-31"),
        (1931, "1931-04-21"), (1936, "1936-04-21"), (1951, "1951-11-04"),
        (1961, "1961-10-15"), (1971, "1971-10-24"), (1981, "1981-10-25"),
    ]
    note = (
        "意大利国家统计局历史统计区界，CC BY 3.0。"
        "省界由2011年市界按当年省归属归并，统计局写明会有近似。不是把今天的大区当作当年的省。"
        "每一档从该普查日或该年12月31日起，到下一档为止。两档之间的改划没有切开。1981年档收到1991年10月20日。"
        "1861年3月17日以前的意大利诸国内部省界不在这里。"
    )
    url = "https://www.istat.it/notizia/confini-statistico-amministrativi-analisi-storica/"
    ends = [item[1] for item in snaps[1:]] + ["1991-10-20"]
    for (year, start), end in zip(snaps, ends):
        zpath = RAW / "istat" / f"Limiti_{year}.zip"
        dest = RAW / "istat" / f"y{year}"
        if not any(dest.rglob("*rovinc*.shp")) and not any(dest.rglob("*rovinc*.SHP")):
            zipfile.ZipFile(zpath).extractall(dest)
        shps = list(dest.rglob("*rovinc*.shp")) + list(dest.rglob("*rovinc*.SHP"))
        shps = [p for p in shps if "circond" not in p.name.lower() and "compart" not in str(p).lower()]
        if not shps:
            raise SystemExit(f"没有省多边形 {year}")
        shp = shps[0]
        info = pyogrio.read_info(shp)
        field = next(col for col in info["fields"] if str(col).upper() in {"DEN_PROV", "DEN_PRO", "PROVINCIA", "NOME"})
        crs, names, blobs, _extra = read_wkb_layer(shp, [field], encoding="cp1252")
        for label, blob in zip(names, blobs):
            if not label:
                continue
            if str(label).startswith("Forl"):
                label = "Forlì"
            add(
                rows, name_src=label, name_zh=zh_lookup(IT, label), kind="省", nominal="意大利王国" if year < 1946 else "意大利",
                start=start, end=end, source_id="istat", license_name="CC BY 3.0", url=url,
                precision=note, geom=reproject(blob, crs), tol=0.015,
            )


def gpkg_rows(db, table):
    con = sqlite3.connect(db)
    try:
        cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})")]
        name_col = "PALATINATE_NAME" if "PALATINATE_NAME" in cols else cols[2]
        for name, blob in con.execute(f"SELECT {name_col}, Shape FROM {table}"):
            flags = blob[3]
            envelope = (flags & 14) >> 1
            offset = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get(envelope, 0)
            yield name, wkb.loads(blob[offset:])
    finally:
        con.close()


def load_poland(rows):
    note = (
        "Paul Dziemiela，1934年波兰第二共和国省界，Public Domain Dedication and License 1.0。"
        "1921年普查省与1934年地图的省分开。1921年档从1921-09-30到1931-01-01。"
        "1931年档从1931-01-01到1938-10-02，不含1938年10月并入的领土。县界没有画。"
    )
    url = "https://dziemiela.com/personal/interwar_poland.html"
    db = RAW / "pl" / "unz" / "Interwar_Poland_1934.gpkg"
    for table, start, end in (
        ("Palatinates_1921", "1921-09-30", "1931-01-01"),
        ("Palatinates", "1931-01-01", "1938-10-02"),
    ):
        for label, geom in gpkg_rows(db, table):
            add(
                rows, name_src=label, name_zh=zh_lookup(PL, label), kind="省", nominal="波兰第二共和国",
                start=start, end=end, source_id="poland-1934", license_name="PDDL 1.0", url=url,
                precision=note, geom=geom, tol=0.015,
            )


def load_uk(rows):
    note = (
        "Historic County Borders Project，定义A简化边界。允许个人、教育、非商业和商业使用，不另需许可。"
        "这是传统郡，不是1889年4月1日以后的行政郡，也不是1974年的郡。"
        "飞地仍按定义A留在原郡，1844年飞地法之后的调整没有切开。海岸是项目的现代岸线。"
        "只包括联合王国的传统郡。爱尔兰岛上后来的26郡不在这套文件里。"
    )
    url = "https://www.county-borders.co.uk/"
    shp = RAW / "uk" / "unz" / "UKDefinitionA.shp"
    _crs, names, blobs, _extra = read_wkb_layer(shp, ["NAME"])
    for label, blob in zip(names, blobs):
        add(
            rows, name_src=label, name_zh=zh_lookup(UK, label), kind="郡", nominal="英国",
            start="1801-01-01", end="1889-04-01", source_id="uk-historic-counties",
            license_name="Historic Counties Trust 允许商业使用", url=url, precision=note,
            geom=wkb.loads(bytes(blob)), tol=0.012,
        )


def load_russia(rows):
    note97 = (
        "Sablin 等，1897年俄罗斯帝国普查省界，海德堡大学 heiDATA，CC BY 4.0，doi:10.11588/data/10064。"
        "只用于1897年。普查日是1897-02-09。前后改划没有沿用这一套。不是今天的联邦主体。"
    )
    note26 = (
        "同一数据集的1926年全苏普查区划，CC BY 4.0。含加盟共和国、自治州和省，不全是帝国省。"
        "只用于1926年。普查日是1926-12-17，年内改划没有切开。"
    )
    url = "https://doi.org/10.11588/data/10064"
    crs, names, blobs, _extra = read_wkb_layer(RAW / "ru" / "1897RussianEmpire.shp", ["NAMEENG"])
    for label, blob in zip(names, blobs):
        kind = "汗国" if "khanate" in label else "埃米尔国" if "emirate" in label else "州" if label.endswith("oblast") or label == "Sakhalin" else "省"
        add(
            rows, name_src=label, name_zh=zh_lookup(RU, label), kind=kind, nominal="俄罗斯帝国",
            start="1897-01-01", end="1898-01-01", source_id="ru-1897", license_name="CC BY 4.0",
            url=url, precision=note97, geom=wkb.loads(bytes(blob)), tol=0.04,
        )
    crs, names, blobs, _extra = read_wkb_layer(RAW / "ru" / "1926SovietUnion.shp", ["NameENG"])
    for label, blob in zip(names, blobs):
        if label.endswith("province"):
            kind = "省"
        elif "ASSR" in label or label.endswith("SSR") or "SFSR" in label:
            kind = "共和国"
        elif label.endswith("region"):
            kind = "边疆区"
        else:
            kind = "自治州"
        add(
            rows, name_src=label, name_zh=zh_lookup(SU, label), kind=kind, nominal="苏联",
            start="1926-01-01", end="1927-01-01", source_id="su-1926", license_name="CC BY 4.0",
            url=url, precision=note26, geom=wkb.loads(bytes(blob)), tol=0.04,
        )


def on(day, start, end) -> bool:
    return (not start or day >= start) and (not end or day < end)


def main():
    rows = []
    load_histogis(rows)
    load_france(rows)
    load_italy(rows)
    load_poland(rows)
    load_uk(rows)
    load_russia(rows)
    missing = sorted({row["name_src"] for row in rows if row["name"] == row["name_src"]})
    features = []
    for index, row in enumerate(rows):
        geom = row.pop("geom")
        row["id"] = f"{row['source_id']}-{index}"
        features.append({"type": "Feature", "properties": row, "geometry": dump_geom(geom)})
    payload = {
        "type": "FeatureCollection",
        "note": "所选日期有来源的欧洲一级行政区。没有列入的国家和年份仍是省界待考。不画今天的省界。",
        "gaps": [
            "法国1790年的 Nakala 文件属性里有1970年以后才使用的省名，并写了 OSM 2020，不能确认不是今天的省界，没有收。1791年至1869年、1941年以后的法国省界待考。",
            "1871年以后的巴伐利亚、符腾堡、巴登、萨克森王国，这份 HistoGIS v3 摘录没有单独几何，待考。普鲁士各省有。阿尔萨斯-洛林作为德国帝国领的几何没有，待考。",
            "西班牙省界没有找到可再分发的历史几何，待考。",
            "罗马尼亚两次大战间的县、南斯拉夫的巴纳特和省，没有找到可再分发的历史几何，待考。",
            "英国1889年4月1日以后的行政郡、1974年的郡，待考。爱尔兰岛上后来不属于联合王国的郡，待考。",
            "意大利1861年3月17日以前诸国的内部省界，待考。诸国本身的国界不在这一层重复。",
            "俄罗斯帝国只收了1897年普查的省。其他年份的省界待考。Imperiia 是 CC BY-NC-SA，没有收。",
            "波兰第二共和国只收了1921年9月30日至1938年10月2日的省。县没有画。",
        ],
        "features": features,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"features {len(features)} bytes {OUT.stat().st_size} untranslated {len(missing)}")
    for item in missing[:40]:
        print("  ?", item)
    from shapely.geometry import Point
    shapes = [(shape(feat["geometry"]), feat["properties"]) for feat in features]
    for day, lon, lat, expect in CHECKS:
        point = Point(lon, lat)
        hits = [prop for geom, prop in shapes if on(day, prop["from"], prop["until"]) and geom.covers(point)]
        hits.sort(key=lambda prop: shape(next(f["geometry"] for f in features if f["properties"] is prop)).area)
        # area already known: recompute from stored geometry is expensive; use prepared order by name length as fallback
        got = hits[0]["name"] if hits else None
        # pick smallest properly
        if len(hits) > 1:
            ranked = []
            for prop in hits:
                geom = next(g for g, p in shapes if p is prop)
                ranked.append((geom.area, prop["name"]))
            ranked.sort()
            got = ranked[0][1]
        flag = "OK" if (expect is None and got is None) or (expect and got and expect in got) else "DIFF"
        print(f"{flag} {day} expect {expect} got {got}")


if __name__ == "__main__":
    main()
