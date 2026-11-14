"""战争审计的退出码。不连服务，也不改 86 条样本。

全部通过必须是 0。任一失败、缺 ok、或一条结果都没有，必须是 1。
华沙公国和 2022-03-15 库皮扬斯克仍在样本里。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import api_mustpass as A
import war_audit as W

problems = []


def check(name, got, want):
    if got != want:
        problems.append(f"{name}: {got} != {want}")
        print("FAIL", name, got)
    else:
        print("PASS", name)


check("全部通过", W.exit_code([{"ok": True}, {"ok": True}]), 0)
check("有一条失败", W.exit_code([{"ok": True}, {"ok": False}]), 1)
check("没有结果", W.exit_code([]), 1)
check("缺 ok 字段", W.exit_code([{"case": "坏了"}]), 1)

warsaw = [row for row in A.C if row[1] == "1808-07-01 华沙=华沙公国"]
kup = [row for row in W.FRONTS if row[0].startswith("2022-03-15") and "库皮扬斯克" in row[0] and row[4] is True]
check("华沙公国仍在样本里", len(warsaw), 1)
check("库皮扬斯克仍要求在控制区内", len(kup), 1)
check("样本仍是 86 条", len(A.C) + len(W.FRONTS), 86)

import io
import contextlib
buf = io.StringIO()
failed = [
    {"group": "拿破仑战争", "case": "1808-07-01 华沙=华沙公国", "ok": False, "errors": ["仍是普鲁士"]},
    {"group": "俄乌战争（前线图层）", "case": "2022-03-15 库皮扬斯克在控制区内", "ok": False, "got": False},
    {"group": "美墨战争", "case": "通过的一条", "ok": True},
]
with contextlib.redirect_stdout(buf):
    code = W.finish(failed)
text = buf.getvalue()
check("有失败时 finish 返回 1", code, 1)
check("汇总写明失败条数", "FAILURES 2" in text, True)
check("失败项点名华沙", "华沙公国" in text, True)
check("失败项点名库皮扬斯克", "库皮扬斯克" in text, True)
check("总数不是写成全部通过", "TOTAL 1/3" in text and "TOTAL 3/3" not in text, True)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = W.finish([{"group": "美墨战争", "case": "一条", "ok": True}])
check("全部通过时 finish 返回 0", code, 0)
check("通过时失败数是 0", "FAILURES 0" in buf.getvalue(), True)

if problems:
    print("FIXTURE_FAIL", len(problems))
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("FIXTURE_OK")
