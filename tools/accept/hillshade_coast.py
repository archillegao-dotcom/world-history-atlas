"""晕渲海岸不能有亮边，透明海水必须是柔光下的中性灰。
用法：python3 tools/accept/hillshade_coast.py
"""
import sys
from PIL import Image
import numpy as np

im = np.asarray(Image.open("frontend/assets/ne50m_hillshade.png"))
if im.shape[2] != 4:
    print("FAIL 不是带透明通道的图")
    sys.exit(1)
rgb, alpha = im[:, :, 0], im[:, :, 3]
water = alpha == 0
land = alpha > 0
bad_water = int((water & (rgb != 128)).sum())
pad = np.pad(water, 1, constant_values=True)
near = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
bright = int((land & near & (rgb > 160)).sum())
print(f"water_not_neutral={bad_water} bright_coast={bright} land={int(land.sum())}")
if bad_water or bright:
    print("FAIL")
    sys.exit(1)
print("PASS")
