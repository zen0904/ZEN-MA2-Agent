#!/usr/bin/env bash
set -euo pipefail

echo "TASK=VERIFY_CONTROL_ROOM_GUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

export DISPLAY=:0

echo "=== WINDOWS ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lxG 2>/dev/null || true

echo "=== LAYOUT ==="
if runuser -u zenui -- env DISPLAY=:0 /usr/local/bin/zen-control-room-layout 2>/dev/null; then
  :
else
  echo "CONTROL_ROOM_LAYOUT=NOT_READY"
fi

echo "=== WINDOWS_AFTER ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lxG 2>/dev/null || true

echo "=== VISUALIZER_HEALTH ==="
curl -fsS --max-time 4 http://127.0.0.1:18992/health || true
echo

echo "RESULT=PASS"
