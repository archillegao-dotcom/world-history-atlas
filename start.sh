#!/bin/bash
# 世界历史地图 启动脚本（macOS / Linux）
# 第一次运行会创建 .venv 并安装依赖（需要联网，约 1 分钟），之后离线即可使用。
cd "$(dirname "$0")" || exit 1
PY=python3
command -v "$PY" >/dev/null 2>&1 || { echo "未找到 python3。请先安装 Python 3.10+：https://www.python.org/downloads/"; exit 1; }
if [ ! -x ".venv/bin/python" ]; then
  echo "首次运行：正在创建运行环境并安装依赖……"
  "$PY" -m venv .venv || exit 1
  .venv/bin/python -m pip install --upgrade pip -q
  .venv/bin/python -m pip install -r requirements.txt -q || { echo "依赖安装失败，请检查网络后重试"; exit 1; }
fi
export WHA_OPEN_BROWSER="${WHA_OPEN_BROWSER:-1}"
exec .venv/bin/python run.py "$@"
