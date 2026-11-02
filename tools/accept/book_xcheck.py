"""
书籍交叉核对：OpenStax《World History》第 1、2 卷（同行评审教科书，CC BY 4.0）中明确写出日期的政权更替，逐条在地图上查询（与面板同一路径）。
每条注明教科书章节网址与原文要点。用法：.venv/bin/python tools/accept/book_xcheck.py → logs/book_xcheck.json
"""
import json, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import api_mustpass as A
A.C.clear(); c = A.c
V1 = "https://openstax.org/books/world-history-volume-1/pages/"
V2 = "https://openstax.org/books/world-history-volume-2/pages/"
SRC = {}
def b(src, quote, *a, **k):
    c(*a, **k); SRC[a[1]] = (src, quote)
b(V1 + "17-1-the-ottomans-and-the-mongols", "On the morning of May 29, 1453 … the city fell to the Ottomans", "OpenStax", "1452-07-01 君士坦丁堡=拜占庭帝国", "1452-07-01", 41.01, 28.98, name=["拜占庭", "东罗马"])
b(V1 + "17-1-the-ottomans-and-the-mongols", "declared it the new capital of the Ottoman Empire", "OpenStax", "1454-07-01 君士坦丁堡=奥斯曼帝国", "1454-07-01", 41.01, 28.98, name=["奥斯曼"])
b(V2 + "2-1-india-and-international-connections", "In 1526 … Babur defeated the much larger army of the Delhi Sultanate … and established the Mughal Empire", "OpenStax", "1525-07-01 德里=德里苏丹国", "1525-07-01", 28.61, 77.21, name=["德里苏丹", "洛迪"])
b(V2 + "2-1-india-and-international-connections", "(同上)", "OpenStax", "1530-07-01 德里=莫卧儿帝国", "1530-07-01", 28.61, 77.21, name=["莫卧儿"])
b(V2 + "7-4-nationalism-liberalism-conservatism-and-the-political-order", "Garibaldi’s declaring Victor Emmanuel II king of the unified kingdom of Italy in 1861", "OpenStax", "1862-07-01 那不勒斯=意大利王国", "1862-07-01", 40.85, 14.27, name=["意大利"])
b(V2 + "7-4-nationalism-liberalism-conservatism-and-the-political-order", "It was completed when Rome was annexed in 1870", "OpenStax", "1869-07-01 罗马=教宗国", "1869-07-01", 41.9, 12.5, name=["教宗国", "教皇国"])
b(V2 + "7-4-nationalism-liberalism-conservatism-and-the-political-order", "(同上)", "OpenStax", "1871-07-01 罗马=意大利王国", "1871-07-01", 41.9, 12.5, name=["意大利"])
b(V2 + "7-4-nationalism-liberalism-conservatism-and-the-political-order", "on January 18, 1871, he was appointed Imperial Chancellor of the German Empire", "OpenStax", "1872-07-01 柏林=德意志帝国", "1872-07-01", 52.52, 13.41, name=["德意志"])
b(V2 + "9-3-colonial-empires", "China signed the Treaty of Shimonoseki in 1895 … Taiwan and the Penghu Islands", "OpenStax", "1894-07-01 台北=清朝", "1894-07-01", 25.03, 121.56, name=["清"])
b(V2 + "9-3-colonial-empires", "(同上)", "OpenStax", "1896-07-01 台北=日本统治", "1896-07-01", 25.03, 121.56, name=["日本", "日据", "日治"])
b(V2 + "9-3-colonial-empires", "Japan formally annexed Korea in 1910", "OpenStax", "1909-07-01 首尔=大韩帝国", "1909-07-01", 37.57, 126.98, name=["大韩帝国", "朝鲜", "韩"])
b(V2 + "9-3-colonial-empires", "(同上)", "OpenStax", "1911-07-01 首尔=日本统治", "1911-07-01", 37.57, 126.98, name=["日本", "日据", "日治", "朝鲜总督府"])
b(V2 + "14-3-the-non-aligned-movement", "at midnight on August 15, 1947, when India achieved its independence, the region of Pakistan … became an independent nation as well", "OpenStax", "1946-07-01 德里=英属印度", "1946-07-01", 28.61, 77.21, name=["英属印度", "英国", "印度"], not_name=["印度共和国"])
b(V2 + "14-3-the-non-aligned-movement", "(同上)", "OpenStax", "1948-07-01 德里=印度", "1948-07-01", 28.61, 77.21, name=["印度"], not_name=["英属"])
b(V2 + "14-3-the-non-aligned-movement", "(同上)", "OpenStax", "1948-07-01 卡拉奇=巴基斯坦", "1948-07-01", 24.86, 67.0, name=["巴基斯坦"])
b(V2 + "14-3-the-non-aligned-movement", "proclaimed independence for Indonesia, a status that became official in 1949", "OpenStax", "1950-07-01 雅加达=印度尼西亚", "1950-07-01", -6.2, 106.85, name=["印度尼西亚", "印尼"])
b(V2 + "14-4-global-tensions-and-decolonization", "on March 6, 1957, Ghana received its independence", "OpenStax", "1956-07-01 阿克拉=黄金海岸", "1956-07-01", 5.6, -0.19, name=["黄金海岸", "英"])
b(V2 + "14-4-global-tensions-and-decolonization", "(同上)", "OpenStax", "1958-07-01 阿克拉=加纳", "1958-07-01", 5.6, -0.19, name=["加纳"])
if __name__ == "__main__":
    res = A.run()
    for r in res:
        r["source"], r["quote"] = SRC[r["case"]]
    json.dump(res, open("logs/book_xcheck.json", "w"), ensure_ascii=False, indent=1)
    tp = sum(r["ok"] for r in res)
    print(f"TOTAL {tp}/{len(res)} = {tp / len(res):.1%}")
