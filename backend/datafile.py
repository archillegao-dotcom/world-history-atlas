"""
数据文件读取：支持 .json.gz（构建脚本输出）和 .json.xz（打包时用 LZMA 重新压缩，体积约小三成）。
调用方一律传入 .json.gz 路径；若同名 .json.xz 存在则优先读取它。
"""
from __future__ import annotations

import gzip
import json
import lzma
from pathlib import Path


def xz_path(path: Path) -> Path:
    return path.with_name(path.name[:-3] + ".xz") if path.name.endswith(".gz") else path


def read_bytes(path: Path) -> bytes | None:
    """返回解压后的内容；文件都不存在时返回 None。"""
    x = xz_path(Path(path))
    if x != path and x.exists():
        return lzma.decompress(x.read_bytes())
    if Path(path).exists():
        return gzip.decompress(Path(path).read_bytes())
    return None


def exists(path: Path) -> bool:
    return xz_path(Path(path)).exists() or Path(path).exists()


def read_json(path: Path, default=None):
    b = read_bytes(path)
    return default if b is None else json.loads(b)
