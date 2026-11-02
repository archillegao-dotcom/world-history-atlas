"""python tools/dev/qs.py REGEX → 匹配 R.states / R.persons / R.offices（en/zh）"""
import re, sys
sys.path.insert(0, ".")
from backend import config
from backend.polity import PolityResolver
R = PolityResolver(config.DATA_DIR)
rx = re.compile(sys.argv[1], re.I)
what = sys.argv[2] if len(sys.argv) > 2 else "s"
src = {"s": R.states, "p": R.persons}.get(what)
if what == "o":
    for o in R.offices:
        if rx.search(o.get("en") or "") or rx.search(o.get("zh") or ""):
            print(o["id"], o.get("pos"), o.get("zh"), o.get("en"), len(o.get("holders", [])))
else:
    for q, s in src.items():
        if rx.search(s.get("en") or "") or rx.search(s.get("zh") or ""):
            print(q, s.get("zh"), s.get("en"), s.get("from"), s.get("to"), len(s.get("hos", [])) if what == "s" else "")
