"""免安装版入口，也可以从源码运行：python launcher.py

* 只读资源（frontend/、历史数据 data/）来自软件包（冻结时是 sys._MEIPASS）；
* 可写数据在每个用户自己的目录里，第一次运行只复制尚不存在的初始文件（不覆盖）：
    macOS   ~/Library/Application Support/WorldHistoryAtlas
    Windows %APPDATA%\\WorldHistoryAtlas
    Linux   ~/.local/share/WorldHistoryAtlas   （尊重 $XDG_DATA_HOME）
  可用 WHA_HOME 或 --home 改这个目录；
* 优先用 8790 端口，被占用就换下一个空闲端口，然后打开默认浏览器；
* 软件已经在运行时再打开一次，只把浏览器带到已有的页面。

平时从源码启动（start.sh / start.bat → python run.py）不受影响，每日新闻仍写在 data/live/。
"""
import argparse
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "WorldHistoryAtlas"
TITLE = "世界历史地图 World History Atlas"
PREFERRED_PORT = 8790
FROZEN = getattr(sys, "frozen", False)
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _fix_stdio():
    # 没有控制台的窗口模式也不能让 print() 崩掉
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:  # noqa: BLE001
            pass
    for name in ("stdout", "stderr"):
        st = getattr(sys, name)
        if st is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
            continue
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def user_home(override=None):
    if override:
        return Path(override).expanduser()
    if os.environ.get("WHA_HOME"):
        return Path(os.environ["WHA_HOME"]).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_NAME


def _first_existing(candidates):
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def bundle_data():
    return _first_existing([BUNDLE / "data", BUNDLE.parent / "data"])


def bundle_frontend():
    return _first_existing([
        BUNDLE / "frontend" / "index.html",
        BUNDLE.parent / "frontend" / "index.html",
    ]).parent


def seed_dir():
    """首次复制到用户目录的小文件（说明文字）。历史数据不复制，一直从软件包里读。"""
    for p in (BUNDLE / "user_seed", BUNDLE / "packaging" / "user_seed"):
        if p.is_dir() and any(p.iterdir()):
            return p
    return None


def copy_seed(seed, data):
    """复制用户目录里还没有的文件（绝不覆盖已有文件）。"""
    n = 0
    for src in seed.rglob("*"):
        if not src.is_file():
            continue
        dst = data / src.relative_to(seed)
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".seedtmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        n += 1
    return n


def _is_our_server(port, timeout=1.5):
    # /api/live/status 不读大文件，适合启动期间反复探测。/api/meta 会统计全部每日新闻，太慢。
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/live/status", timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
            return r.status == 200 and "interval_minutes" in body and "last_added" in body
    except Exception:  # noqa: BLE001
        return False


def _pid_alive(pid):
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _existing_server(info_file, wait=45):
    """软件正在启动（数据还在加载）时，等到它能回答再复用，而不是再开一个。"""
    try:
        old = json.loads(info_file.read_text(encoding="utf-8"))
        port = int(old["port"])
        pid = int(old.get("pid") or 0)
    except Exception:  # noqa: BLE001
        return None
    deadline = time.time() + wait
    while True:
        if _is_our_server(port):
            return port
        if pid and not _pid_alive(pid):
            return None
        if time.time() >= deadline:
            return port if _is_our_server(port) else None
        time.sleep(0.4)


def _bind(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":
        s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR), 1)
    else:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(128)
        return s
    except OSError:
        s.close()
        return None


def bind_port(preferred, strict=False):
    """自己先占住端口（避免两个进程抢同一个）。指定了端口就只用它，否则再试后面 20 个，最后任意端口。"""
    cands = [preferred] if strict else [preferred] + list(range(preferred + 1, preferred + 21)) + [0]
    for p in cands:
        s = _bind(p)
        if s is not None:
            return s, s.getsockname()[1]
    raise SystemExit(f"[!] 端口 {preferred} 已被占用，无法启动。 / Port {preferred} is busy.")


def _open_browser_when_ready(url, port):
    for _ in range(240):
        if _is_our_server(port, timeout=1):
            break
        time.sleep(0.5)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass


def _terminal_relaunch_script(executable, argv):
    """终端真正会执行的脚本。

    `open -a Terminal <二进制>` 并不能稳定地跑一个裸可执行文件。.command 可以，
    而且 exec 让服务留在这个窗口里，关掉窗口就是退出。
    带上 --no-terminal，新进程不会再把自己打开一次。
    """
    args = [x for x in argv if not str(x).startswith("-psn")]
    if "--no-terminal" not in args:
        args.append("--no-terminal")
    cmd = " ".join(shlex.quote(p) for p in [str(executable), *args])
    return "#!/bin/bash\nexec " + cmd + "\n"


def _mac_relaunch_in_terminal(home):
    """从访达打开 .app 时没有控制台。把内部的二进制交给「终端」，用户能看到状态，关掉窗口即退出。
    成功交给终端时返回 True。"""
    if not (FROZEN and sys.platform == "darwin" and ".app/Contents/MacOS/" in sys.executable):
        return False
    try:
        if sys.stdin is not None and sys.stdin.isatty():
            return False  # 已经在终端里（或是 .command 拉起的子进程）
    except Exception:  # noqa: BLE001
        pass
    marker = home / ".terminal_relaunch"
    try:
        if marker.exists() and time.time() - marker.stat().st_mtime < 20:
            return False  # 防止死循环：终端启动后仍然没有 tty
        home.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(time.time()), encoding="utf-8")
        script = home / "launch.command"
        script.write_text(_terminal_relaunch_script(sys.executable, sys.argv[1:]), encoding="utf-8")
        os.chmod(script, 0o755)
        return subprocess.run(["open", "-a", "Terminal", str(script)], timeout=30).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _use_certifi():
    try:
        import certifi
        ca = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
    except Exception:  # noqa: BLE001
        pass


def _pause_on_error():
    if FROZEN and os.name == "nt":
        try:
            input("按回车键关闭窗口 / Press Enter to close ...")
        except Exception:  # noqa: BLE001
            pass


def main():
    _fix_stdio()
    # 分析阶段如果把这个变量留在环境里，运行时也要清掉，否则服务不会加载数据。
    os.environ.pop("WHA_PYINSTALLER_ANALYZE", None)
    ap = argparse.ArgumentParser(description=TITLE)
    ap.add_argument("--port", type=int, default=None, help="端口（默认 8790，被占用时自动换一个）")
    ap.add_argument("--home", default=None, help="可写数据目录（默认按系统放在用户目录）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--no-terminal", action="store_true", help="macOS：不在终端窗口中重新打开")
    a, _unknown = ap.parse_known_args()  # 忽略 macOS 的 -psn_* 参数

    home = user_home(a.home)
    info_file = home / "server.json"
    # 再点一次只打开浏览器，不要再开一个终端窗口。
    existing = _existing_server(info_file)
    if existing:
        url = f"http://localhost:{existing}/"
        print(f"{TITLE} 已在运行：{url}")
        if not a.no_browser:
            print("已为你打开浏览器")
            webbrowser.open(url)
        time.sleep(3)
        return
    if not a.no_terminal and _mac_relaunch_in_terminal(home):
        return
    if a.no_terminal:
        # 冒烟测试和终端里的子进程走这里。这一行故意只用 ASCII，方便 CI 在日志里查找。
        print(">> --no-terminal: staying in this process", flush=True)

    data = bundle_data()
    front = bundle_frontend()
    os.environ["WHA_DATA_DIR"] = str(data)
    os.environ["WHA_FRONTEND_DIR"] = str(front)
    # 冻结后（以及用 launcher 启动时）每日新闻和缓存只写用户目录，不写软件包。
    os.environ["WHA_USER_DATA_DIR"] = str(home)
    home.mkdir(parents=True, exist_ok=True)
    _use_certifi()

    if not (data / "basemaps" / "index.json").is_file():
        raise SystemExit(f"[!] 找不到地图数据：{data / 'basemaps' / 'index.json'}")

    seed = seed_dir()
    if seed is not None:
        n = copy_seed(seed, home)
        if n:
            print(f">> 首次运行：已将 {n} 个初始文件复制到 {home}（已有文件不会覆盖）")

    env_port = os.environ.get("WHA_PORT")
    port_req = a.port or (int(env_port) if env_port else None)
    sock, port = bind_port(port_req or PREFERRED_PORT, strict=port_req is not None)
    url = f"http://localhost:{port}/"
    info_file.write_text(json.dumps({"port": port, "pid": os.getpid(), "started": time.time()}),
                         encoding="utf-8")

    print("=" * 60)
    print(f"  {TITLE} 已启动")
    print(f"  浏览器地址：{url}")
    print(f"  只读历史数据：{data}")
    print(f"  每日新闻与缓存：{home}")
    print("  ★ 关闭此窗口即可退出（或按 Ctrl+C）。")
    print("=" * 60, flush=True)

    if not a.no_browser:
        threading.Thread(target=_open_browser_when_ready, args=(url, port), daemon=True).start()

    import uvicorn
    from backend.app import app
    try:
        uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[sock])
    finally:
        try:
            if json.loads(info_file.read_text(encoding="utf-8")).get("pid") == os.getpid():
                info_file.unlink()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e.code if isinstance(e.code, str) else f"[!] exit {e.code}")
            _pause_on_error()
            sys.exit(1)
        raise
    except BaseException as e:  # noqa: BLE001
        if isinstance(e, KeyboardInterrupt):
            sys.exit(0)
        import traceback
        traceback.print_exc()
        print(f"[!] 启动失败：{e}")
        _pause_on_error()
        sys.exit(1)
