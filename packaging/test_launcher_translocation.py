"""App Translocation 不能再被写进 launch.command。

不启动服务，三个构建任务和冒烟脚本都会跑它：
    python packaging/test_launcher_translocation.py
"""
import os
import shlex
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from launcher import (  # noqa: E402
    _terminal_relaunch_script,
    is_app_translocated,
    scrub_translocated_launch_command,
    should_relaunch_in_terminal,
    try_terminal_relaunch,
)

# 用户机器上失败的那种路径（UUID 已换成示例）。
TRANS = ("/private/var/folders/ab/xyz/T/AppTranslocation/"
         "8E3C1A0B-1234-5678-9ABC-DEF012345678/d/"
         "WorldHistoryAtlas.app/Contents/MacOS/WorldHistoryAtlas")
STABLE = "/Applications/WorldHistoryAtlas.app/Contents/MacOS/WorldHistoryAtlas"


def check(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)


def main():
    check(is_app_translocated(TRANS), "user's App Translocation path was not detected")
    check(not is_app_translocated(STABLE), "Applications path was treated as translocated")
    check(not is_app_translocated(""), "empty path")

    link_root = Path(tempfile.mkdtemp())
    real = link_root / "AppTranslocation" / "UUID" / "d"
    real.mkdir(parents=True)
    exe = real / "WorldHistoryAtlas"
    exe.write_text("x", encoding="utf-8")
    link = link_root / "WorldHistoryAtlas"
    link.symlink_to(exe)
    check(is_app_translocated(link), "symlink to App Translocation was not detected")
    check("AppTranslocation" not in str(link), "the symlink path itself should not contain the marker")

    kw = dict(frozen=True, platform="darwin", isatty=False, no_terminal=False)
    check(not should_relaunch_in_terminal(executable=TRANS, **kw), "would relaunch a translocated app")
    check(should_relaunch_in_terminal(executable=STABLE, **kw), "stable .app should still use Terminal")
    check(not should_relaunch_in_terminal(executable=STABLE, frozen=True, platform="darwin",
                                          isatty=False, no_terminal=True), "--no-terminal must stay in-process")
    check(not should_relaunch_in_terminal(executable=STABLE, frozen=True, platform="darwin",
                                          isatty=True, no_terminal=False), "an existing tty must not relaunch")
    check(not should_relaunch_in_terminal(executable=STABLE, frozen=False, platform="darwin",
                                          isatty=False, no_terminal=False), "source runs must not relaunch")
    check(not should_relaunch_in_terminal(executable=STABLE, frozen=True, platform="win32",
                                          isatty=False, no_terminal=False), "Windows must not relaunch Terminal")

    try:
        _terminal_relaunch_script(TRANS, [])
        raise SystemExit("FAIL: script builder accepted a translocated path")
    except ValueError:
        pass
    body = _terminal_relaunch_script(STABLE, ["--no-browser"])
    check("AppTranslocation" not in body, "stable script mentioned App Translocation")
    check("--no-terminal" in body, "relaunch script dropped --no-terminal")
    check(STABLE in body, "stable executable missing from the script")

    home = Path(tempfile.mkdtemp())
    bad = home / "launch.command"
    bad.write_text("#!/bin/bash\nexec " + shlex.quote(TRANS) + " --no-terminal\n", encoding="utf-8")
    os.chmod(bad, 0o755)
    check(scrub_translocated_launch_command(home), "did not remove the broken launch.command")
    check(not bad.exists(), "broken launch.command still on disk")

    called = []

    def opener(script):
        called.append(script.read_text(encoding="utf-8"))
        return 0

    ok = try_terminal_relaunch(
        home, executable=TRANS, argv=[], frozen=True, platform="darwin", isatty=False, opener=opener,
    )
    check(ok is False, "translocated relaunch returned success")
    check(called == [], "opener was called for a translocated app")
    check(not (home / "launch.command").exists(), "wrote launch.command for a translocated app")

    ok = try_terminal_relaunch(
        home, executable=STABLE, argv=["-psn_0_123"], frozen=True, platform="darwin", isatty=False, opener=opener,
    )
    check(ok is True, "stable relaunch did not succeed")
    check(len(called) == 1, "opener call count")
    check("AppTranslocation" not in called[0], "written script points at App Translocation")
    check(STABLE in called[0], "written script lost the stable path")
    check("-psn_" not in called[0], "macOS -psn argument was forwarded")
    check("--no-terminal" in called[0], "written script lost --no-terminal")

    home2 = Path(tempfile.mkdtemp())

    def boom(_script):
        raise OSError("Terminal.app did not start")

    ok = try_terminal_relaunch(
        home2, executable=STABLE, argv=[], frozen=True, platform="darwin", isatty=False, opener=boom,
    )
    check(ok is False, "a failed Terminal open must stay in-process")
    text = (home2 / "launch.command").read_text(encoding="utf-8")
    check("AppTranslocation" not in text, "failure path still wrote a translocated script")

    home3 = Path(tempfile.mkdtemp())
    ok = try_terminal_relaunch(
        home3, executable=STABLE, argv=[], frozen=True, platform="darwin", isatty=False, opener=lambda _s: 1,
    )
    check(ok is False, "non-zero open must stay in-process")
    print("translocation relaunch guard ok")


if __name__ == "__main__":
    main()
