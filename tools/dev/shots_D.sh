#!/bin/bash
# 战争前线（俄乌）截图 → screenshots/v07/
cd /workspace/world_history
B=http://127.0.0.1:8792; O=screenshots/v07; mkdir -p $O
S() { .venv/bin/python tools/screenshot.py $B "$1" "$O/$2" || echo "FAIL $2"; }
S "#date=2018-06-01&c=48.3,34&z=6&layers=war_fronts" 10_war_2018_baseline.png
S "#date=2022-03-15&c=48.3,34&z=6&layers=war_fronts" 11_war_2022-03-15_ISW.png
S "#date=2022-11-15&c=48.3,34&z=6&layers=war_fronts" 12_war_2022-11-15_DeepState.png
S "#date=2026-11-01&c=48.3,34&z=6&layers=war_fronts" 13_war_2026-11-01_latest.png
echo ALLDONE
