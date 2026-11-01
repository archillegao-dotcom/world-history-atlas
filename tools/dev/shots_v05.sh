#!/bin/bash
# 阶段 A 验证截图 → screenshots/v05/
cd /workspace/world_history
B=http://127.0.0.1:8792; O=screenshots/v05; mkdir -p $O
S() { .venv/bin/python tools/screenshot.py $B "$1" "$O/$2" || echo "FAIL $2"; }
S "#date=1950-06-01&name=China&tab=leaders&c=36,112&z=4" 01_1950-06-01_China_PRC_leaders.png
S "#date=1950-06-01&name=Taiwan&tab=leaders&c=30,118&z=5" 02_1950-06-01_Taiwan_ROC_leaders.png
S "#date=1950-06-01&world=1&c=42,120&z=4" 03_1950-06-01_NE_Asia_no_Manchukuo.png
S "#date=2020-06-01&name=China&tab=leaders" 04_2020-06-01_PRC_leaders.png
S "#date=2020-06-01&name=Taiwan&tab=leaders&c=30,118&z=5" 05_2020-06-01_ROC_Taiwan_leaders.png
S "#date=-1448&name=Sinic&tab=leaders&c=34,114&z=4" 06_-1448_China_Shang.png
S "#date=-5000&world=1&c=35,40&z=3" 07_-5000_world.png
S "#date=-3000&world=1&c=35,40&z=3" 08_-3000_world.png
S "#date=1990-06-01&name=British%20Hong%20Kong&tab=leaders&c=22.35,114.15&z=9" 09_1990-06-01_HongKong_British.png
S "#date=2020-06-01&name=Hong%20Kong&tab=leaders&c=22.35,114.15&z=9" 10_2020-06-01_HongKong_SAR.png
S "#date=1842-08-29&treaty=Q238262" 11_treaty_Nanjing_1842.png
S "#date=1980-06-01&name=Portuguese%20Macau&tab=leaders&c=22.2,113.55&z=10" 12_1980-06-01_Macau_Portuguese.png
echo ALLDONE
