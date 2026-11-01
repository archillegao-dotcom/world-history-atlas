#!/bin/bash
# 重启测试服务器（端口 8792）。只结束 cwd 为本项目的 run.py 进程，不碰 8765 等其他应用。
cd /workspace/world_history
for p in $(pgrep -f "run.py"); do
  [ "$(readlink /proc/$p/cwd)" = "/workspace/world_history" ] && kill $p
done
for i in $(seq 1 20); do ss -ltn | grep -q "127.0.0.1:8792 " || break; sleep 0.5; done
WHA_PORT=8792 WHA_AUTO_UPDATE=0 nohup .venv/bin/python run.py > logs/server.log 2>&1 &
for i in $(seq 1 90); do
  if ss -ltnp | grep "127.0.0.1:8792 " | grep -q "pid=$!,"; then echo "up on 8792 (pid $!)"; exit 0; fi; sleep 1
done
echo "server not up on 8792"; tail -20 logs/server.log; exit 1
