#!/usr/bin/env bash
set -euo pipefail

R=/opt/zen/zen-ops-runtime
SESSION=/usr/local/libexec/zen-chatgpt-session.sh
LAYOUT=/usr/local/bin/zen-control-room-layout
BACKUP=/usr/local/libexec/zen-chatgpt-session.sh.pre-control-room-20260930

echo "TASK=INSTALL_CONTROL_ROOM_GUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -f "$R/deploy/ubuntu/zen-chatgpt-session.sh"
test -f "$R/deploy/ubuntu/zen-control-room-layout"

if [[ ! -e "$BACKUP" && -f "$SESSION" ]]; then
  cp -a "$SESSION" "$BACKUP"
fi

install -m 0755 "$R/deploy/ubuntu/zen-chatgpt-session.sh" "$SESSION"
install -m 0755 "$R/deploy/ubuntu/zen-control-room-layout" "$LAYOUT"

systemctl restart zen-chatgpt-desktop.service
sleep 8

echo "CHATGPT_SERVICE=$(systemctl is-active zen-chatgpt-desktop.service 2>/dev/null || true)"
echo "VISUALIZER_SERVICE=$(systemctl is-active zen-living-visualizer.service 2>/dev/null || true)"
echo "VISUALIZER_HEALTH=$(curl -fsS --max-time 4 http://127.0.0.1:18992/health 2>/dev/null || true)"
echo "=== WINDOWS ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>&1 || true
echo "=== LAYOUT ==="
runuser -u zenui -- env DISPLAY=:0 /usr/local/bin/zen-control-room-layout 2>&1 || true
echo "RESULT=PASS"
