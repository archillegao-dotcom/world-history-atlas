@echo off
REM 世界历史地图 启动脚本（Windows）：双击运行
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 首次运行：正在创建运行环境并安装依赖……
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 ( echo 未找到 Python，请先安装 Python 3.10+ & pause & exit /b 1 )
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
)
set WHA_OPEN_BROWSER=1
".venv\Scripts\python.exe" run.py
pause
