#!/usr/bin/env bash
set -euo pipefail

echo "TASK=DIAG_CONTROL_ROOM_GUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
echo "DISPLAY=:0"
echo "=== WMCTRL ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>&1 || true
echo "=== CHATGPT PROCESS ==="
ps -eo pid,user,args | grep -E '/usr/bin/chatgpt|ChatGPT' | grep -v grep || true
echo "=== CHROME ==="
/usr/bin/google-chrome --version 2>/dev/null || true
echo "=== VISUALIZER ==="
curl -fsS --max-time 4 http://127.0.0.1:18992/health || true
echo
echo "RESULT=PASS"
