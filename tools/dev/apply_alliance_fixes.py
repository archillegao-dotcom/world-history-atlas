"""把 data/curated/alliance_member_fixes.json 应用到 data/alliances.json.gz，并丢弃倒序的成员区间。"""
import sys, json, gzip, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def key(d):
    return None if not d else d["y"] + (d.get("m") or 6.5) / 12.5

def apply(al):
    fx = json.loads((ROOT / "data/curated/alliance_member_fixes.json").read_text(encoding="utf-8"))
    n_fix = n_drop = 0
    for a in al:
        f = fx.get(a["id"], {})
        mem = []
        for m in a.get("members", []):
            if m["s"] in f:
                continue
            if key(m.get("from")) is not None and key(m.get("to")) is not None and key(m["to"]) < key(m["from"]):
                n_drop += 1
                continue
            mem.append(m)
        for s, rec in f.items():
            if s.startswith("_"):
                continue
            for r in rec["members"]:
                mem.append({"s": s, "from": r["from"], "to": r["to"], "via": "curated"})
                n_fix += 1
        a["members"] = mem
    return al, n_fix, n_drop

if __name__ == "__main__":
    p = ROOT / "data/alliances.json.gz"
    al = json.load(gzip.open(p, "rt", encoding="utf-8"))
    al, a, b = apply(al)
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(al, fh, ensure_ascii=False)
    print("curated members", a, "dropped reversed", b)
