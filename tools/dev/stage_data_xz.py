"""把运行时数据拷到发布暂存目录，并把 .json.gz / .geojson.gz 重新压缩为 .xz（与仓库 v0.4.1 的约定一致）。
用法：python tools/dev/stage_data_xz.py <src_data> <dest_data>"""
import gzip, lzma, os, shutil, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SKIP = {"basemaps_raw", "cache", "econ_raw", "xcheck_raw", "live", "wiki_cache", "__pycache__", "cshapes_raw", "ww2_raw"}

def conv(a):
    src, dst = a
    data = gzip.decompress(Path(src).read_bytes())
    Path(dst).write_bytes(lzma.compress(data, preset=9 | lzma.PRESET_EXTREME))
    return len(data)

def main(src, dst):
    src, dst = Path(src), Path(dst)
    jobs = []
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if rel.parts[0] in SKIP or any(x in SKIP for x in rel.parts) or p.is_dir():
            continue
        if p.name.endswith((".bak", ".tmp")) or ".bak" in p.name:
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if p.name.endswith(".gz"):
            jobs.append((str(p), str(out.with_name(p.name[:-3] + ".xz"))))
        else:
            shutil.copy2(p, out)
    with ProcessPoolExecutor(max_workers=int(os.environ.get("XZ_WORKERS", "0")) or None) as ex:
        list(ex.map(conv, jobs, chunksize=16))
    print("converted", len(jobs))

if __name__ == "__main__":
    main(*sys.argv[1:3])
