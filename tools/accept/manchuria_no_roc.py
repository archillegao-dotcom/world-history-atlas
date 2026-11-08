"""回归测试：1932-03 至 1945-08 每月，东北（黑吉辽 + 1933-03 起热河）网格点不得解析为中华民国，且满洲国只有一个多边形。
用法：WHA_PORT=8792 python tools/accept/manchuria_no_roc.py   （需要开发服务器在运行）"""
import json, os, sys, urllib.request
PORT = os.environ.get("WHA_PORT", "8792")
PTS = [(45.75, 126.65, "哈尔滨"), (49.9, 127.2, "黑河南"), (46.8, 130.35, "佳木斯"), (49.2, 119.75, "海拉尔"),
       (43.88, 125.32, "长春"), (41.8, 123.43, "沈阳"), (38.92, 121.6, "大连周边(关东州除外)"), (42.9, 129.5, "延吉"),
       (44.0, 121.0, "兴安南"), (47.3, 123.9, "齐齐哈尔"), (40.5, 124.1, "丹东北")]
JEHOL = [(40.97, 117.93, "承德"), (42.27, 118.95, "赤峰")]
bad, months = [], 0
for y in range(1932, 1946):
    for m in range(1, 13):
        if (y, m) < (1932, 3) or (y, m) > (1945, 8):
            continue
        d = f"{y}-{m:02d}-15"; months += 1
        pts = PTS + (JEHOL if (y, m) >= (1933, 4) else [])
        fids = set()
        for lat, lon, nm in pts:
            if nm.startswith("大连"):
                continue
            p = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/locate?date={d}&lat={lat}&lon={lon}"))["polity"] or {}
            n = (p.get("NAME_ZH") or "") + "|" + (p.get("NAME") or "")
            if "满洲" not in n and "Manchu" not in n:
                bad.append((d, nm, p.get("fid"), n))
            else:
                fids.add(p.get("fid"))
        if len(fids) > 1:
            bad.append((d, "多个满洲国多边形", sorted(fids), ""))
print(f"months={months} failures={len(bad)}")
for b in bad[:40]:
    print("  FAIL", *b)
sys.exit(1 if bad else 0)
