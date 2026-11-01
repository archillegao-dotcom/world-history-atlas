"""
源码启动入口（start.sh / start.command / start.bat 调用它）。
免安装版不走这里，入口是 launcher.py。
  python run.py            # 默认 127.0.0.1:8790；端口被占用时自动顺延
  WHA_PORT=8800 python run.py
"""
import socket
import sys
import threading
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402

from backend import config  # noqa: E402


def free_port(host: str, start: int) -> int:
    for p in range(start, start + 20):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # 刚关闭的端口（TIME_WAIT）也能重新使用
            try:
                s.bind((host, p))
                return p
            except OSError:
                print(f"端口 {p} 已被占用，尝试下一个… / port {p} busy")
    raise SystemExit("找不到可用端口 / no free port")


def main():
    port = free_port(config.HOST, config.PORT)
    url = f"http://{config.HOST}:{port}/"
    print(f"世界历史地图已启动：{url}  （关闭此窗口即停止）")
    if config.OPEN_BROWSER:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    from backend.app import app
    uvicorn.run(app, host=config.HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
