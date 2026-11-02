# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — build with:  python packaging/build.py
#
# onedir（不是 onefile）：启动大约一两秒，而不是每次先把一两百 MB 解到临时目录。
# macOS 上整个 .app 只需在「右键 → 打开」里批准一次。
# 产物：dist/WorldHistoryAtlas/           （Windows / Linux，运行 WorldHistoryAtlas[.exe]）
#       dist/WorldHistoryAtlas.app        （仅 macOS）
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
SEED = ROOT / "build" / "seed_data"
if not (SEED / "events.json.xz").is_file() or not (SEED / "basemaps" / "index.json").is_file():
    raise SystemExit("build/seed_data missing — run: python packaging/build.py")
if not (ROOT / "frontend" / "index.html").is_file():
    raise SystemExit("frontend/index.html missing")
VERSION = os.environ.get("WHA_VERSION", "0.6.1").lstrip("v") or "0.6.1"

# 分析阶段会 import backend.app。那个导入会装载全部历史数据，这里跳过。
os.environ["WHA_PYINSTALLER_ANALYZE"] = "1"
os.environ.setdefault("WHA_DATA_DIR", str(SEED))
os.environ.setdefault("WHA_USER_DATA_DIR", str(ROOT / "build" / "analyze-user"))

datas = [
    (str(ROOT / "frontend"), "frontend"),
    (str(SEED), "data"),
    # 冻结后 pkgutil 看不到 PYZ 里的模块；把 .py 放进包里，启动时按文件名发现模块。
    (str(ROOT / "backend" / "modules"), "backend/modules"),
    (str(ROOT / "packaging" / "user_seed"), "user_seed"),
]
hiddenimports = (collect_submodules("uvicorn") + collect_submodules("backend.modules")
                 + collect_submodules("backend.live")
                 + ["backend.app", "backend.config", "backend.geo", "backend.registry",
                    "backend.datafile", "backend.timeutil", "backend.polity", "backend.details",
                    "backend.econ", "backend.control_zones", "backend.official",
                    "backend.territory_info", "backend.transitions",
                    "backend.cshapes", "backend.ww2", "backend.flags", "backend.regimes", "backend.china_eras", "backend.interregna", "backend.zh", "backend.geolock", "certifi", "tzdata", "shapely", "shapely.geometry"])
excludes = ["tkinter", "_tkinter", "IPython", "jupyter", "notebook", "pytest",
            "PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib", "PIL",
            "scipy", "pandas", "requests", "opencc"]
hiddenimports = [h for h in hiddenimports if not any(h == e or h.startswith(e + ".") for e in excludes)]

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)
is_mac = sys.platform == "darwin"
icon = None
for cand in (ROOT / "packaging" / ("icon.icns" if is_mac else "icon.ico"),):
    if cand.exists():
        icon = str(cand)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="WorldHistoryAtlas",
    console=not is_mac,          # Windows/Linux：控制台显示状态，关掉窗口即退出。
                                 # macOS：.app 会在「终端」里重新打开自己（见 launcher.py）。
    upx=False,                   # UPX 会破坏 macOS 签名，也容易让杀毒软件误报
    strip=False,
    argv_emulation=False,
    target_arch=None,            # 用构建机自己的架构（arm64 或 x86_64）
    codesign_identity=None,      # macOS 上 PyInstaller 会做 ad-hoc 签名（Apple 芯片必须有签名）
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="WorldHistoryAtlas")

if is_mac:
    app = BUNDLE(
        coll,
        name="WorldHistoryAtlas.app",
        icon=icon,
        bundle_identifier="org.worldhistoryatlas.app",
        version=VERSION,
        info_plist={
            "CFBundleName": "WorldHistoryAtlas",
            "CFBundleDisplayName": "世界历史地图",
            "CFBundleShortVersionString": VERSION,
            "LSUIElement": True,                 # 短暂的启动进程不占用程序坞图标
            "NSHighResolutionCapable": True,
            # 占位。packaging/build.py 会改成实际链接进来的二进制所要求的最低系统版本，然后重新签名。
            "LSMinimumSystemVersion": "11.0",
        },
    )
