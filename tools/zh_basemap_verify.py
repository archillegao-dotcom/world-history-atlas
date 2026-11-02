"""核对底图名称补译（zh_basemap_names.json）：英文维基同名条目可能是同名的别的东西（如 Fox → 狐、Waka Waka → 歌曲）。
取英文条目对应的 Wikidata 项及其 P31（是……的实例），属于明显不是政权/族群/地区/人物的类别（生物分类、歌曲、电影、专辑、消歧义页、标点、公司、体育队等），
或译名不含汉字的，判为不可靠并删除（显示原名 + 「暂无通用译名」）。被删的写入 logs/zh_basemap_rejected.json 供人工核对。"""
import json, time, urllib.parse, urllib.request
from pathlib import Path
D = Path("data"); P = D / "curated/zh_basemap_names.json"
BAD = {"Q16521": "生物分类", "Q4167410": "消歧义页", "Q7366": "歌曲", "Q134556": "单曲", "Q482994": "专辑", "Q11424": "电影", "Q5398426": "电视剧",
       "Q7889": "电子游戏", "Q105543609": "音乐作品", "Q4830453": "公司", "Q215380": "乐队", "Q476028": "足球俱乐部", "Q12136": "疾病",
       "Q1668024": "标点/符号", "Q9788": "字母", "Q3331189": "版本/译本", "Q7725634": "文学作品", "Q47461344": "书面作品", "Q571": "书",
       "Q13406463": "维基列表", "Q1004": "漫画", "Q15416": "电视节目", "Q2088357": "音乐团体", "Q55488": "铁路车站", "Q11032": "报纸",
       "Q4022": "河流", "Q8502": "山", "Q23397": "湖", "Q11173": "化合物", "Q12140": "药物", "Q1190554": "事件", "Q178561": "战役",
       "Q2221906": "地理位置", "Q41176": "建筑", "Q1248784": "机场", "Q2385804": "教育机构", "Q3918": "大学", "Q11446": "船", "Q1420": "汽车"}
UA = {"User-Agent": "WorldHistoryAtlas/0.6.1 (research; box)"}
def get(u):
    for k in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception: time.sleep(3 * (k + 1))
    return {}
d = json.loads(P.read_text()); names = d["names"]
todo = {n: v for n, v in names.items() if v}
rej = {}
titles = {v["title"]: n for n, v in todo.items()}
tl = list(titles)
qid_of = {}
for i in range(0, len(tl), 40):
    r = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item|disambiguation", "titles": "|".join(tl[i:i+40]), "format": "json"}))
    for p in r.get("query", {}).get("pages", {}).values():
        pp = p.get("pageprops", {})
        n = titles.get(p["title"])
        if n is None: continue
        if "disambiguation" in pp: rej[n] = "消歧义页"
        elif pp.get("wikibase_item"): qid_of[n] = pp["wikibase_item"]
    time.sleep(0.3)
ql = list(set(qid_of.values())); p31 = {}
for i in range(0, len(ql), 50):
    r = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ql[i:i+50]), "props": "claims", "format": "json"}))
    for q, e in r.get("entities", {}).items():
        p31[q] = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P31", [])]
    time.sleep(0.5)
import re
for n, v in todo.items():
    if n in rej: continue
    if not re.search(r"[\u4e00-\u9fff]", v["zh"]): rej[n] = "译名无汉字"; continue
    hit = [BAD[c] for c in p31.get(qid_of.get(n), []) if c in BAD]
    if hit: rej[n] = "同名条目是" + "/".join(hit)
for n, why in rej.items():
    names[n] = None
Path("logs/zh_basemap_rejected.json").write_text(json.dumps({n: {"why": w, **todo[n]} for n, w in rej.items()}, ensure_ascii=False, indent=1))
d["_verify"] = __doc__ + f"\n删除 {len(rej)} 条。"
P.write_text(json.dumps(d, ensure_ascii=False, indent=0))
print("checked", len(todo), "rejected", len(rej), "kept", sum(1 for v in names.values() if v))
print(list(rej.items())[:40])

# —— 人工复核（v0.6.1）：自动核对后仍逐条看了保留的 245 条。以下按人工判断处理 ——
# 删：英文同名条目是别的东西（城市/现代行政区代替同名部族、语言代替族群、普通名词）
MANUAL_REJECT = ["?", "Air", "Birria", "Coca", "Crow", "Fox", "Hail", "Kali", "Nasa", "Pagan", "Palas", "Rama", "Chisos", "Chiapaneco", "Gondwana",
                 "Miami", "Omaha", "Peoria", "Peoria (Oklahoma)", "Biloxi", "Erie", "Spokane", "Yakima", "Waco", "Sumas", "Wahkiakum", "Perquimans",
                 "Calvas", "Paltas", "Iñapari", "Clatskanie", "Ucluelet", "Yoncalla", "Sisseton", "Pawtucket", "Opelousas", "Mississauga", "Okanagan",
                 "Cholulteca", "Ambur", "Gooty", "Pasto", "Tonokoté", "Northern Pomo", "Chamicuro", "Hixkaryana", "Yinggarda", "Mon-Khmer", "Sura"]
# 恢复：自动规则误删的地区名（底图本身就是地区标签）
MANUAL_RESTORE = {"Africa": "非洲", "Oxus": "阿姆河", "Kanas": "喀纳斯", "Lake Vygozero": "维戈泽罗湖"}
# 改：中文维基链接名是现代行政区名，历史地图上用通行的历史名称
MANUAL_FIX = {"Tonkin": "北圻", "Xinjiang": "新疆", "Tibet": "西藏", "Madras": "马德拉斯"}
def manual():
    d = json.loads(P.read_text()); names = d["names"]
    for n in MANUAL_REJECT:
        names[n] = None
    for n, z in MANUAL_RESTORE.items():
        names[n] = {"zh": z, "src": "英文维基同名条目的中文维基链接（人工复核恢复）"}
    for n, z in MANUAL_FIX.items():
        names[n] = {"zh": z, "src": "人工复核：历史通行名称"}
    P.write_text(json.dumps(d, ensure_ascii=False, indent=0))
    print("after manual: kept", sum(1 for v in names.values() if v))
manual()
