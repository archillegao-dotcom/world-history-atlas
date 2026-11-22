#!/usr/bin/env python3
"""墨西哥革命、俄国内战：只标有日子的驻地。没有历史界线的不画。服务需已在 8792。"""
import json
import os
import sys
import urllib.request

BASE = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
FAIL = 0


def get(url):
    with urllib.request.urlopen(BASE + url, timeout=60) as r:
        return json.load(r)


def check(label, ok, detail=""):
    global FAIL
    if ok:
        print("PASS", label)
    else:
        FAIL += 1
        print("FAIL", label, detail)


def ids(date):
    pack = get(f"/api/layers/control_zones?date={date}")
    return pack, {i["id"] for i in pack["items"]}


pack, have = ids("1913-11-15")
check("1913-11-15 有华雷斯活动点", "mx_villa_juarez_1913" in have, have)
ju = next(i for i in pack["items"] if i["id"] == "mx_villa_juarez_1913")
check("华雷斯是活动点不是辖境", ju.get("activity_only") and "不是辖境" in (ju.get("note") or "") and "待考" in (ju.get("note") or ""), ju.get("note"))
check("华雷斯不写成奇瓦瓦州", "不画奇瓦瓦州" in (ju.get("note") or ""), ju.get("note"))

_, d16 = ids("1913-11-16")
check("11月16日不顺延华雷斯", "mx_villa_juarez_1913" not in d16, d16)

_, ch = ids("1913-11-26")
check("11月26日有奇瓦瓦城活动点", "mx_villa_chihuahua_1913" in ch, ch)
_, ch2 = ids("1913-11-27")
check("11月27日不顺延奇瓦瓦城", "mx_villa_chihuahua_1913" not in ch2, ch2)

pack, omsk = ids("1919-07-01")
check("1919-07-01 有鄂木斯克驻地", "ru_kolchak_omsk" in omsk, omsk)
ko = next(i for i in pack["items"] if i["id"] == "ru_kolchak_omsk")
check("鄂木斯克不是西伯利亚", ko.get("activity_only") and "不是西伯利亚" in (ko.get("note") or ""), ko.get("note"))
check("名义所属仍写在说明里", "名义" in (ko.get("note") or ""), ko.get("note"))
_, after = ids("1919-11-14")
check("11月14日鄂木斯克驻地拿掉", "ru_kolchak_omsk" not in after, after)

undrawn = {i["id"] for i in pack.get("undrawn") or []}
for key in ("mx-carranza", "mx-zapata", "mx-obregon", "ru-denikin", "ru-wrangel", "ru-green", "ru-fer", "ru-ethnic", "jp-sengoku"):
    check(f"未画清单有{key}", key in undrawn, sorted(undrawn))
blob = json.dumps(pack.get("undrawn"), ensure_ascii=False)
check("未画清单写明待考", "待考" in blob and "不画" in blob, blob[:180])
check("日本战国不新造", "不新造" in blob, "")

print("FAIL", FAIL)
sys.exit(1 if FAIL else 0)
