#!/bin/bash
# macOS：在“访达”中双击本文件即可启动。
# 首次打开如被系统拦截：右键点击本文件 -> 打开。
cd "$(dirname "$0")" || exit 1
/bin/bash ./start.sh ${1+"$@"}
status=$?
if [ "${status}" -ne 0 ]; then
  echo ""
  echo "启动失败（代码 ${status}），按回车关闭窗口。"
  read -r _
fi
exit "${status}"
