"""
集中配置：所有路径与端口都从这里取，均可用环境变量覆盖，便于将来 PyInstaller 打包
（打包后 sys._MEIPASS 指向解包目录；数据目录可放在可执行文件旁边，单独更新）。

环境变量 / Env overrides:
  WHA_HOST          监听地址，默认 127.0.0.1
  WHA_PORT          端口，默认 8790
  WHA_DATA_DIR      数据目录（basemaps/ events.json.gz people_*.json.gz）
  WHA_FRONTEND_DIR  前端静态文件目录
  WHA_OPEN_BROWSER  1=启动后自动打开浏览器（启动脚本默认开启）
  WHA_USER_DATA_DIR 自动更新数据（每日新闻）写入的目录；默认 DATA_DIR/live（不可写时用系统用户数据目录）
  WHA_AUTO_UPDATE   1=后台自动抓取每日新闻（默认 1），0=关闭（完全离线）
  WHA_UPDATE_MINUTES 自动更新间隔（分钟，默认 60）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _app_root() -> Path:
    # PyInstaller onefile/onedir: 资源解包在 sys._MEIPASS
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


APP_ROOT = _app_root()


def _data_default() -> Path:
    # 打包后优先使用可执行文件旁边的 data/（便于单独更新数据）
    if getattr(sys, "frozen", False):
        side = Path(sys.executable).parent / "data"
        if side.exists():
            return side
    return APP_ROOT / "data"


HOST = os.environ.get("WHA_HOST", "127.0.0.1")
PORT = int(os.environ.get("WHA_PORT", "8790"))
DATA_DIR = Path(os.environ.get("WHA_DATA_DIR", _data_default()))
FRONTEND_DIR = Path(os.environ.get("WHA_FRONTEND_DIR", APP_ROOT / "frontend"))
BASEMAP_DIR = DATA_DIR / "basemaps"
OPEN_BROWSER = os.environ.get("WHA_OPEN_BROWSER", "0") == "1"
APP_VERSION = "0.4.0"
AUTO_UPDATE = os.environ.get("WHA_AUTO_UPDATE", "1") == "1"
UPDATE_MINUTES = max(5, int(os.environ.get("WHA_UPDATE_MINUTES", "60")))


def _user_data_default() -> Path:
    cand = DATA_DIR / "live"
    try:
        cand.mkdir(parents=True, exist_ok=True)
        probe = cand / ".write_test"
        probe.write_text("ok")
        probe.unlink()
        return cand
    except OSError:
        pass
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "WorldHistoryAtlas"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", home)) / "WorldHistoryAtlas"
    return home / ".local" / "share" / "WorldHistoryAtlas"


USER_DATA_DIR = Path(os.environ.get("WHA_USER_DATA_DIR", _user_data_default()))
