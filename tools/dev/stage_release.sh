#!/usr/bin/env bash
# 组装发布暂存目录（参照 v0.5.0）：代码与文档原样复制，data/ 由 stage_data_xz.py 转成 .xz。
# 用法：bash tools/dev/stage_release.sh /workspace/wh_v060_stage
set -euo pipefail
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
DST="$1"
rm -rf "$DST"; mkdir -p "$DST"
cd "$SRC"
.venv/bin/python - "$DST" <<'PY'
import shutil, sys, fnmatch
from pathlib import Path
dst = Path(sys.argv[1])
TOP_SKIP = {".venv", "logs", "data", "screenshots", "dist", "build", ".git"}
PAT = ["__pycache__", "*.pyc", "*.bak", "*.bak_*", "*.bak.*", "*.tmp", "premerge_v050"]
def ign(d, names):
    out = {n for n in names if any(fnmatch.fnmatch(n, p) for p in PAT)}
    if Path(d).resolve() == Path(".").resolve():
        out |= {n for n in names if n in TOP_SKIP}
    return out
shutil.copytree(".", dst, ignore=ign, dirs_exist_ok=True)
PY
mkdir -p "$DST/data"
XZ_WORKERS="${XZ_WORKERS:-2}" .venv/bin/python tools/dev/stage_data_xz.py data "$DST/data"
# 截图：只带 v0.6.1 的用户式截图 screenshots/v09（不含逐国点击截图）
mkdir -p "$DST/screenshots/v09"
cp screenshots/v09/*.png "$DST/screenshots/v09/" 2>/dev/null || true
mkdir -p "$DST/screenshots/v09b"; cp screenshots/v09b/*.png "$DST/screenshots/v09b/" 2>/dev/null || true
du -sh "$DST" "$DST/data"
