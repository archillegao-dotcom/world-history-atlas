"""把发布暂存目录打成若干 zip 分卷（每卷 < 25 MB，参照 v0.5.0）：解压到同一目录即合成完整的 world-history-atlas/。
用法：python tools/dev/make_parts.py <stage_dir> <out_prefix>   例：/workspace/wh_v060_stage /workspace/wh_v060_part
分卷：1 = 代码、文档与小数据；2 = data/basemaps + data/current_events；3 = data/war_fronts；4 = screenshots（有则单独一卷）。超过上限会报错。"""
import sys, zipfile
from pathlib import Path
LIMIT = 25 * 1024 * 1024
stage, prefix = Path(sys.argv[1]), sys.argv[2]
TOP = "world-history-atlas"
groups = {2: ("data/basemaps/", "data/current_events/"), 3: ("data/war_fronts/",), 4: ("screenshots/",)}
files = sorted(p for p in stage.rglob("*") if p.is_file())
parts = {1: [], 2: [], 3: [], 4: []}
for p in files:
    rel = p.relative_to(stage).as_posix()
    n = next((k for k, pre in groups.items() if rel.startswith(pre)), 1)
    parts[n].append((p, rel))
for n, items in parts.items():
    if not items:
        continue
    out = Path(f"{prefix}{n}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p, rel in items:
            z.write(p, f"{TOP}/{rel}")
    sz = out.stat().st_size
    print(f"{out} {len(items)} files {sz} bytes ({sz / 1048576:.1f} MiB)")
    if sz >= LIMIT:
        raise SystemExit(f"{out} 超过 25 MB")
