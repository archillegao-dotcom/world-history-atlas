"""一键本地打包：python packaging/build.py   （需要：pip install -r requirements.txt pyinstaller）

生成 dist/WorldHistoryAtlas/（macOS 上还有 dist/WorldHistoryAtlas.app）以及 dist/ 里的 zip：
  WorldHistoryAtlas-<系统>-<架构>.zip

macOS 的 zip 用 ditto 打，这样 .app 里的符号链接和签名才不会丢。
LSMinimumSystemVersion 按实际链进来的二进制来写，然后重新做 ad-hoc 签名
（改 Info.plist 会让 PyInstaller 原来的签名失效）。
"""
import os
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
}


def run(*cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def stage_seed():
    """把 data/ 拷到 build/seed_data，去掉运行时才产生的可写目录（live、缓存）。"""
    src = ROOT / "data"
    dest = ROOT / "build" / "seed_data"
    if not (src / "events.json.xz").is_file() or not (src / "basemaps" / "index.json").is_file():
        raise SystemExit(f"historical data missing under {src}")
    if dest.exists():
        shutil.rmtree(dest)

    def ignore(_dir, names):
        skip = set()
        for n in names:
            if n in {"live", "wiki_cache", "__pycache__", ".DS_Store"} or n.endswith(".tmp") or n.startswith("._"):
                skip.add(n)
        return skip

    shutil.copytree(src, dest, ignore=ignore)
    print(f"staged seed data → {dest}", flush=True)


def _ver_tuple(text):
    parts = []
    for piece in text.split("."):
        if not piece.isdigit():
            return None
        parts.append(int(piece))
    return tuple(parts) if parts else None


def _norm(parts):
    parts = tuple(parts[:3])
    return parts + (0,) * (3 - len(parts))


def format_minos(parts):
    """'11.0'、'10.15' 或 '14.1.2' —— 至少有主版本和次版本。"""
    major, minor, patch = _norm(parts)
    if patch:
        return f"{major}.{minor}.{patch}"
    return f"{major}.{minor}"


def parse_otool_minos(text):
    """一个 Mach-O（含每个切片）声明的最低系统版本。

    LC_BUILD_VERSION 里的 version 是链接器版本，不是系统版本。那里只看 minos。
    更老的二进制用 LC_VERSION_MIN_MACOSX。
    """
    mins = []
    cmd = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("cmd "):
            cmd = stripped.split(None, 1)[1]
            continue
        if cmd == "LC_BUILD_VERSION" and stripped.startswith("minos "):
            parsed = _ver_tuple(stripped.split(None, 1)[1])
        elif cmd == "LC_VERSION_MIN_MACOSX" and stripped.startswith("version "):
            parsed = _ver_tuple(stripped.split(None, 1)[1])
        else:
            continue
        if parsed and parsed[0] > 0:
            mins.append(parsed)
    return mins


def scan_minos(app):
    """返回包里要求最高的那个最低系统版本：(version_tuple, relative_path)。"""
    best = None
    best_path = None
    ranked = []
    for path in app.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            magic = path.read_bytes()[:4]
        except OSError:
            continue
        if magic not in _MACHO_MAGICS:
            continue
        proc = subprocess.run(["otool", "-l", str(path)], capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            continue
        found = parse_otool_minos(proc.stdout)
        if not found:
            continue
        top = max(found, key=_norm)
        rel = str(path.relative_to(app))
        ranked.append((_norm(top), rel))
        if best is None or _norm(top) > _norm(best):
            best, best_path = top, rel
    if best is None:
        raise SystemExit("could not read a minimum macOS version from the .app (otool found no Mach-O minos)")
    ranked.sort(reverse=True)
    print("highest minimum macOS versions in the bundle:", flush=True)
    for ver, rel in ranked[:8]:
        print(f"  {format_minos(ver):8} {rel}", flush=True)
    return best, best_path


def set_minimum_system_version(app):
    version, source = scan_minos(app)
    text = format_minos(version)
    plist_path = app / "Contents" / "Info.plist"
    with plist_path.open("rb") as fh:
        plist = plistlib.load(fh)
    plist["LSMinimumSystemVersion"] = text
    with plist_path.open("wb") as fh:
        plistlib.dump(plist, fh)
    print(f"LSMinimumSystemVersion={text} required by {source}", flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"- LSMinimumSystemVersion **{text}** (required by `{source}`)\n")
    return text


def clean_pycache():
    """本地跑过源码后再打包时，不要把 __pycache__ 打进软件包。"""
    for base in (ROOT / "backend", ROOT / "frontend"):
        for p in base.rglob("__pycache__"):
            shutil.rmtree(p, ignore_errors=True)


def main():
    clean_pycache()
    extra = [a for a in sys.argv[1:] if a != "--fetch"]
    if extra:
        print("note: ignoring extra args (historical data is already in the repo):", " ".join(extra))
    if sys.platform == "darwin":
        # 不要让从源码编译的轮子继承构建机的 macOS 版本（macos-latest 已经是 26）。
        # 预编译轮子保留它自己构建时的版本；下面的扫描会读出真正的要求。
        os.environ.setdefault("MACOSX_DEPLOYMENT_TARGET", "11.0")
    os.environ["WHA_PYINSTALLER_ANALYZE"] = "1"
    stage_seed()
    run(sys.executable, "-m", "PyInstaller", "packaging/world_history_atlas.spec", "--noconfirm", "--clean")
    osname = {"darwin": "macos", "win32": "windows"}.get(sys.platform, "linux")
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(
        platform.machine().lower(), platform.machine().lower())
    dist = ROOT / "dist"
    out = dist / f"WorldHistoryAtlas-{osname}-{arch}.zip"
    out.unlink(missing_ok=True)
    if sys.platform == "darwin":
        app = dist / "WorldHistoryAtlas.app"
        set_minimum_system_version(app)
        # Info.plist 改过了，原来的 ad-hoc 签名失效。
        # Apple 芯片拒绝启动签名损坏或没有签名的包。
        run("codesign", "--force", "--deep", "--sign", "-", str(app))
        run("codesign", "--verify", "--deep", "--verbose=2", str(app))
        # ditto 保留 .app 里的符号链接和签名（zip -r 不行）
        run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(out))
    else:
        shutil.make_archive(str(out.with_suffix("")), "zip", dist, "WorldHistoryAtlas")
    print(f"built {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
