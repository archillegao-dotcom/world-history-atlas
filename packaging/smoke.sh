#!/usr/bin/env bash
# 启动打包好的程序并访问本机接口。
# macOS 上先解 ditto 打的 zip，测的就是用户下载到的那个包（符号链接 + ad-hoc 签名），
# 并用 --no-terminal 启动。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# 不依赖打包结果：App Translocation 路径绝不能写进 launch.command。
if command -v python >/dev/null 2>&1; then
  python packaging/test_launcher_translocation.py
else
  python3 packaging/test_launcher_translocation.py
fi

RUNNER_OS="${RUNNER_OS:-}"
if [ -z "$RUNNER_OS" ]; then
  case "$(uname -s)" in
    Darwin) RUNNER_OS=macOS ;;
    MINGW*|MSYS*|CYGWIN*) RUNNER_OS=Windows ;;
    *) RUNNER_OS=Linux ;;
  esac
fi

WORKDIR="${RUNNER_TEMP:-/tmp}/wha-smoke"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
export WHA_HOME="$WORKDIR/home"
export WHA_AUTO_UPDATE=0
export PYTHONUNBUFFERED=1
LOG="$WORKDIR/wha.log"

if [ "$RUNNER_OS" = "macOS" ]; then
  ZIP="$(echo dist/WorldHistoryAtlas-macos-*.zip)"
  test -f "$ZIP"
  ditto -x -k "$ZIP" "$WORKDIR/unpacked"
  APP="$WORKDIR/unpacked/WorldHistoryAtlas.app"
  BIN="$APP/Contents/MacOS/WorldHistoryAtlas"
  test -x "$BIN"
  if ! find "$APP" -name events.json.xz | grep -q .; then
    echo "seed data missing from the unpacked .app"
    find "$APP/Contents" -maxdepth 4 -type d -o -type l | head -n 80
    exit 1
  fi
  if ! find "$APP" -type l | grep -q .; then
    echo "unpacked .app has no symlinks; ditto did not preserve the bundle"
    exit 1
  fi
  echo "codesign of unpacked app:"
  codesign --verify --deep --verbose=2 "$APP"
  echo "LSMinimumSystemVersion=$(plutil -extract LSMinimumSystemVersion raw "$APP/Contents/Info.plist")"
else
  if [ "$RUNNER_OS" = "Windows" ]; then
    BIN="$ROOT/dist/WorldHistoryAtlas/WorldHistoryAtlas.exe"
  else
    BIN="$ROOT/dist/WorldHistoryAtlas/WorldHistoryAtlas"
  fi
  test -f "$BIN"
  if ! find "$ROOT/dist/WorldHistoryAtlas" -name events.json.xz | grep -q .; then
    echo "seed data missing from dist/WorldHistoryAtlas"
    exit 1
  fi
fi

"$BIN" --port 18790 --no-browser --no-terminal >"$LOG" 2>&1 </dev/null &
PID=$!

cleanup() {
  kill "$PID" 2>/dev/null || true
  if [ "$RUNNER_OS" = "Windows" ]; then
    taskkill //F //IM WorldHistoryAtlas.exe >/dev/null 2>&1 || true
  fi
  echo "----- packaged app log -----"
  cat "$LOG" 2>/dev/null || true
  if [ -f "$WORKDIR/second.log" ]; then
    echo "----- second launch -----"
    cat "$WORKDIR/second.log" || true
  fi
}
trap cleanup EXIT

for _ in $(seq 1 90); do
  if curl -sf --max-time 5 http://127.0.0.1:18790/api/live/status -o "$WORKDIR/status.json"; then
    break
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "packaged app exited before /api/live/status responded"
    exit 1
  fi
  sleep 2
done
test -s "$WORKDIR/status.json"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
"$PY" packaging/smoke_check.py http://127.0.0.1:18790 "$WHA_HOME"

# 第二次启动应发现已有进程，只打开浏览器（这里用了 --no-browser），不应再占一个端口。
"$BIN" --no-browser --no-terminal >"$WORKDIR/second.log" 2>&1 </dev/null
grep -F "已在运行" "$WORKDIR/second.log"
grep -F -- "--no-terminal: staying in this process" "$LOG"
echo "smoke test ok"
