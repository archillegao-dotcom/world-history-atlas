#!/bin/bash
# 用法: tools/dev/shot.sh "<#片段>" 输出.png   （无头 Chrome，1440x900）
U="http://127.0.0.1:8792/$1"
timeout 90 google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1440,900 \
  --virtual-time-budget=25000 --screenshot="$2" "$U" >/dev/null 2>&1
ls -la "$2" 2>/dev/null | awk '{print $5, $9}'
