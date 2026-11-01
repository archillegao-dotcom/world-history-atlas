"""
集中配置：所有路径与端口都从这里取，均可用环境变量覆盖。

环境变量 / Env overrides:
  WHA_HOST          监听地址，默认 127.0.0.1
  WHA_PORT          端口，默认 8790
  WHA_DATA_DIR      只读历史数据（basemaps/ events.json.xz …）。
                    源码运行默认是仓库里的 data/；免安装版默认是软件包内的数据（只读种子）。
  WHA_FRONTEND_DIR  前端静态文件目录
  WHA_OPEN_BROWSER  1=启动后自动打开浏览器（启动脚本默认开启；免安装版由 launcher.py 打开）
  WHA_USER_DATA_DIR 可写目录：每日新闻更新与维基百科缓存。
                    源码运行默认 data/live（写不进去时改用下面的用户目录）。
                    免安装版一律用用户目录，不往软件包里写：
                      macOS   ~/Library/Application Support/WorldHistoryAtlas
                      Windows %APPDATA%\\WorldHistoryAtlas
                      Linux   ~/.local/share/WorldHistoryAtlas
  WHA_AUTO_UPDATE   1=后台自动抓取每日新闻（默认 1），0=关闭（完全离线）
  WHA_UPDATE_MINUTES 自动更新间隔（分钟，默认 60）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "WorldHistoryAtlas"


def _app_root() -> Path:
    # PyInstaller onefile/onedir：资源在 sys._MEIPASS（只读种子数据、前端）
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


APP_ROOT = _app_root()


def per_user_dir() -> Path:
    """免安装版（以及 data/live 不可写时）的个人数据目录。"""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        return (Path(base) if base else home / "AppData" / "Roaming") / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") / APP_NAME


def _data_default() -> Path:
    # 打包后的历史数据在软件包里，只读。不要改用可执行文件旁边的 data/：
    # 用户把 App 解压到自己的文件夹时那个位置往往可写，更新会写进软件包。
    return APP_ROOT / "data"


HOST = os.environ.get("WHA_HOST", "127.0.0.1")
PORT = int(os.environ.get("WHA_PORT", "8790"))
DATA_DIR = Path(os.environ.get("WHA_DATA_DIR", _data_default()))
FRONTEND_DIR = Path(os.environ.get("WHA_FRONTEND_DIR", APP_ROOT / "frontend"))
BASEMAP_DIR = DATA_DIR / "basemaps"
OPEN_BROWSER = os.environ.get("WHA_OPEN_BROWSER", "0") == "1"
APP_VERSION = "0.5.0"
AUTO_UPDATE = os.environ.get("WHA_AUTO_UPDATE", "1") == "1"
UPDATE_MINUTES = max(5, int(os.environ.get("WHA_UPDATE_MINUTES", "60")))


def _user_data_default() -> Path:
    if getattr(sys, "frozen", False):
        return per_user_dir()
    cand = DATA_DIR / "live"
    try:
        cand.mkdir(parents=True, exist_ok=True)
        probe = cand / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return cand
    except OSError:
        return per_user_dir()


USER_DATA_DIR = Path(os.environ["WHA_USER_DATA_DIR"]).expanduser() if os.environ.get("WHA_USER_DATA_DIR") else _user_data_default()
