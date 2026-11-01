#!/bin/bash
# 阶段 B 补拍（首都修正、蒙古控制区、西汉皇帝）→ screenshots/v06_stageB/
cd /workspace/world_history
B=http://127.0.0.1:8792; O=screenshots/v06_stageB; mkdir -p $O
S() { .venv/bin/python tools/screenshot.py $B "$1" "$O/$2" || echo "FAIL $2"; }
S "#date=0220-06-01&name=Han&tab=leaders&c=33,112&z=4" 02_0220-06-01_China_EasternHan.png
S "#date=-0200&name=Han%20Empire&tab=leaders&c=33,112&z=4" 15_-0200_WesternHan_LiuBang.png
echo ALLDONE
