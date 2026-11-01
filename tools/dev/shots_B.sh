#!/bin/bash
# 阶段 B 验证截图 → screenshots/v06_stageB/
cd /workspace/world_history
B=http://127.0.0.1:8792; O=screenshots/v06_stageB; mkdir -p $O
S() { .venv/bin/python tools/screenshot.py $B "$1" "$O/$2" || echo "FAIL $2"; }
S "#date=-1300&name=Zhoa&tab=leaders&c=34,114&z=4" 01_-1300_China_Shang.png
S "#date=0220-06-01&name=Han&tab=leaders&c=33,112&z=4" 02_0220-06-01_China_EasternHan.png
S "#date=0500&name=Toba%20Wei&tab=leaders&c=33,114&z=4" 03_0500_China_NorthernWei.png
S "#date=1000&name=Song%20Empire&tab=leaders&c=33,114&z=4" 04_1000_China_NorthernSong.png
S "#date=1150&name=Northern%20China%20under%20the%20Jin%20dynasty&tab=leaders&c=33,114&z=4&layers=control_zones" 05_1150_China_Jin_SouthernSong.png
S "#date=1990-06-01&name=British%20Hong%20Kong&tab=leaders&c=22.35,114.15&z=9" 06_1990-06-01_HongKong_British.png
S "#date=2020-06-01&name=Hong%20Kong%20S.A.R.&tab=leaders&c=22.35,114.15&z=9" 07_2020-06-01_HongKong_SAR.png
S "#date=1950-03-15&name=Hainan%20Island%20(ROC-held)&tab=leaders&c=22,112&z=6&layers=control_zones" 08_1950-03-15_SouthChina_Hainan_ROC.png
S "#date=1950-06-15&name=China&tab=leaders&c=22,112&z=6&layers=control_zones" 09_1950-06-15_SouthChina_Hainan_PRC.png
S "#date=1950-06-15&c=23,103&z=5&layers=control_zones&world=1" 10_1950-06-15_SW_KMT_Burma_zone.png
S "#date=1980-06-01&name=Portuguese%20Macau&tab=leaders&c=22.2,113.55&z=10" 11_1980-06-01_Macau_governor.png
S "#date=1997-08-01&name=Hong%20Kong%20S.A.R.&tab=leaders&c=22.35,114.15&z=9" 12_1997-08-01_HongKong_SAR_noQC.png
S "#date=1841-06-01&name=Manchu%20Empire&tab=leaders&c=22.6,113.8&z=7" 13_1841-06-01_HK_not_separate.png
echo ALLDONE
