#!/usr/bin/env python3
"""
打包发布用的 zip：
  - 排除 .venv、截图、日志、缓存（data/cache）、原始底图（data/basemaps_raw）、用户数据（data/live）、__pycache__；
  - 数据文件 *.json.gz / *.geojson.gz 在包内改用 LZMA（.xz，preset 9e）重新压缩——内容完全不变，
    体积约小三成；程序读取时优先读 .xz（backend/datafile.py、backend/geo.py）。
  - start.sh / start.command 设为可执行。
用法：python tools/make_zip.py [输出路径，默认 /workspace/world_history_app.zip]
"""
from __future__ import annotations

import gzip
import lzma
import os
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/workspace/world_history_app.zip")
PREFIX = "world_history"
EXCLUDE_DIRS = {".venv", "screenshots", "logs", "__pycache__", ".git"}
EXCLUDE_DATA = {"cache", "basemaps_raw", "live", "wiki_cache", "econ_raw", "xcheck_raw"}


def recompress(path: str) -> bytes:
    return lzma.compress(gzip.decompress(Path(path).read_bytes()), preset=9 | lzma.PRESET_EXTREME)


def files():
    for dp, dns, fns in os.walk(ROOT):
        rel = Path(dp).relative_to(ROOT)
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS and not (rel == Path("data") and d in EXCLUDE_DATA)]
        for f in fns:
            if f.endswith((".pyc", ".tmp")) or f == ".DS_Store":
                continue
            yield Path(dp) / f


def main():
    all_files = sorted(files())
    gz = [p for p in all_files if p.name.endswith(".gz") and "data" in p.relative_to(ROOT).parts]
    with ProcessPoolExecutor() as ex:
        xz = dict(zip(gz, ex.map(recompress, [str(p) for p in gz], chunksize=4)))
    before = after = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in all_files:
            rel = p.relative_to(ROOT).as_posix()
            if p in xz:
                before += p.stat().st_size
                after += len(xz[p])
                info = zipfile.ZipInfo(f"{PREFIX}/{rel[:-3]}.xz", date_time=(2026, 11, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                z.writestr(info, xz[p], compress_type=zipfile.ZIP_STORED)   # 已压缩，不再 deflate
                continue
            info = zipfile.ZipInfo.from_file(p, f"{PREFIX}/{rel}")
            info.external_attr = (0o755 if p.name in ("start.sh", "start.command") else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    print(f"data gz {before/1e6:.1f} MB -> xz {after/1e6:.1f} MB; zip {OUT.stat().st_size/1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
