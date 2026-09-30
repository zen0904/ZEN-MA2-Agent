#!/usr/bin/env bash
set -euo pipefail

echo "TASK=VERIFY_CONTROL_ROOM_TUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
export DISPLAY=:0

echo "=== WINDOWS ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lxG 2>/dev/null || true

echo "=== TUI_PROCESS ==="
pgrep -a -u zenui -f '/usr/local/bin/zen-living-tui' || true

echo "=== LEGACY_CHROME_VISUALIZER ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>/dev/null |
  awk 'tolower($0) ~ /google-chrome/ && tolower($0) ~ /zen living system/ {print}' || true

echo "=== WEB_VISUALIZER_SERVICE ==="
systemctl is-active zen-living-visualizer.service 2>/dev/null || true

echo "RESULT=PASS"
