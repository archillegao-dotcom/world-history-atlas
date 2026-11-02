import sys, collections, json; sys.path.insert(0,'.')
from backend import config
from backend.polity import PolityResolver
from backend.geo import BasemapStore
from backend.timeutil import HDate
B=BasemapStore(); R=PolityResolver(config.DATA_DIR); R.geo=B
miss=collections.defaultdict(list)
for y in range(1886, 2027):
    d=HDate(y,7,1); snap=B.snapshot_at(d)
    for fid,f in B.features(snap).items():
        if not (300000 <= fid < 400000): continue
        p=R.primary(R.resolve(snap,fid,d),d)
        if not p:
            pr=B.polity(snap,fid)["props"]
            miss[(pr.get("CSHAPES"), pr.get("NAME"), pr.get("STATUS"))].append(y)
out=[{"gw":k[0],"name":k[1],"status":k[2],"years":[v[0],v[-1],len(v)]} for k,v in sorted(miss.items(), key=lambda x:-len(x[1]))]
json.dump(out, open("data/audit/unresolved_cs.json","w"), ensure_ascii=False, indent=0)
for o in out: print(o)
