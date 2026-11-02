#!/bin/bash
cd /workspace/world_history
for a in "$@"; do timeout 200 .venv/bin/python tools/dev/q.py $a 2>&1 | head -2 | cut -c1-240; done
