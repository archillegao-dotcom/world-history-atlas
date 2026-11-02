"""预热 CShapes 合成缓存：python tools/dev/warm_cs.py FROM TO NPROC"""
import sys, time
from multiprocessing import Pool
sys.path.insert(0, '.')
from backend.geo import BasemapStore
B = None
def init():
    global B
    B = BasemapStore()
def run(m):
    t = time.time()
    try:
        B.cs.compose(f"cs@{m}")
        return m, round(time.time() - t, 1), None
    except Exception as e:
        return m, 0, repr(e)
if __name__ == "__main__":
    lo, hi, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    b = BasemapStore()
    from backend.timeutil import HDate
    ms = sorted({b.cs.vid(HDate(m // 10000, m // 100 % 100, m % 100))[3:] for m in b.cs.marks if lo <= m < hi})
    print(len(ms), "marks", flush=True)
    with Pool(n, initializer=init) as p:
        for r in p.imap_unordered(run, ms):
            print(*r, flush=True)
