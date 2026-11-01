#!/bin/bash
# 金朝全境修正截图 → screenshots/v07/
cd /workspace/world_history
B=http://127.0.0.1:8792; O=screenshots/v07; mkdir -p $O
S() { .venv/bin/python tools/screenshot.py $B "$1" "$O/$2" || echo "FAIL $2"; }
S "#date=1124-07-01&name=Liao&tab=leaders&c=38,115&z=4&layers=control_zones" 01_1124_Liao_before_fall.png
S "#date=1130-07-01&name=Jin%20dynasty%20realm%20(former%20Liao%20lands%20and%20North%20China)&tab=leaders&c=38,115&z=4&layers=control_zones" 02_1130_Jin_realm.png
S "#date=1150-07-01&name=Jin%20dynasty%20realm%20(former%20Liao%20lands%20and%20North%20China)&tab=leaders&c=38,115&z=4&layers=control_zones" 03_1150_Jin_realm.png
echo ALLDONE
