"""没有中文也没有英文标签的人物、职位、组织（多为只在 Wikidata 有条目的地方官员）：取 Wikidata 任一语言的标签作为原名，
显示为「原名（暂无通用译名）」，不再显示裸 QID。→ data/curated/orig_labels.json"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, ".")
from backend.datafile import read_json
UA = {"User-Agent": "WorldHistoryAtlas/0.6.1 (research; box)"}
D = Path("data")
recs = list(read_json(D / "persons.json.gz", [])) + list(read_json(D / "offices.json.gz", [])) + list(read_json(D / "orgs.json.gz", []))
ru = read_json(D / "rulers.json.gz", {}) or {}
recs += list(ru.get("offices", [])) + list(read_json(D / "ruler_persons.json.gz", []) or [])
recs += list((read_json(D / "ruler_fills.json.gz", {}) or {}).get("persons", []))
# v0.6.1：职位、组织也一样（如波兰立陶宛宫廷官职 Q9394451 łożniczy 只有波兰语等标签，面板上曾显示裸 QID）
qs = sorted({r["id"] for r in recs if isinstance(r, dict) and r.get("id", "").startswith("Q") and not r.get("zh") and not r.get("en")})
out = {}
PREF = ["mul", "en", "de", "fr", "es", "it", "pt", "nl", "pl", "ru", "uk", "cs", "sv", "ca", "hu", "ro", "tr", "ar", "fa", "ja", "ko"]
for i in range(0, len(qs), 50):
    for k in range(4):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "wbgetentities", "ids": "|".join(qs[i:i+50]), "props": "labels", "format": "json"}), headers=UA), timeout=60)); break
        except Exception:
            time.sleep(5 * (k + 1)); r = {}
    for q, e in r.get("entities", {}).items():
        L = e.get("labels", {})
        lang = next((l for l in PREF if l in L), next(iter(L), None))
        if lang:
            out[q] = {"label": L[lang]["value"], "lang": lang}
    time.sleep(0.5)
(D / "curated/orig_labels.json").write_text(json.dumps({"_doc": __doc__, "labels": out}, ensure_ascii=False, indent=0))
print(len(qs), "found", len(out), list(out.items())[:8])
