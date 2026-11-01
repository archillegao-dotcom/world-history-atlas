import sys,collections; sys.path.insert(0,'.')
from backend import config
from backend.geo import BasemapStore
from backend.polity import PolityResolver
from backend.timeutil import HDate
sys.path.insert(0,'tools'); from audit import primary
B=BasemapStore(); R=PolityResolver(config.DATA_DIR); R.geo=B
for y in [int(a) for a in sys.argv[1:]]:
    d=HDate(y,7 if y>0 else 0,1 if y>0 else 0); s=B.snapshot_at(d); fs=B.features(s)
    um=[f["props"].get("NAME") for fid,f in fs.items() if primary(R.resolve(s,fid,d),d) is None]
    print(y,s,len(fs),"unmatched",len(um), collections.Counter(um).most_common(12))
