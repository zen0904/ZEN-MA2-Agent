#!/usr/bin/env bash
set -euo pipefail

echo "TASK=REPAIR_CONTROL_ROOM_GUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

export DISPLAY=:0

windows="$(runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>/dev/null || true)"
if ! printf '%s\n' "$windows" | grep -qi 'google-chrome'; then
  runuser -u zenui -- env \
    HOME=/var/lib/zenui \
    USER=zenui \
    LOGNAME=zenui \
    DISPLAY=:0 \
    XDG_CONFIG_HOME=/var/lib/zenui/.config \
    /usr/bin/google-chrome \
      --app=http://127.0.0.1:18992/ \
      --user-data-dir=/var/lib/zenui/.config/zen-living-chrome \
      --no-first-run \
      --disable-session-crashed-bubble \
      --disable-features=Translate \
      --ozone-platform=x11 \
      >/var/lib/zenui/visualizer-chrome.log 2>&1 &
  echo "VISUALIZER_LAUNCH=STARTED"
else
  echo "VISUALIZER_LAUNCH=ALREADY_PRESENT"
fi

ready=0
for _ in $(seq 1 20); do
  windows="$(runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>/dev/null || true)"
  if printf '%s\n' "$windows" | grep -qi 'google-chrome'; then
    ready=1
    break
  fi
  sleep 0.5
done

if [[ "$ready" != "1" ]]; then
  echo "VISUALIZER_WINDOW=NOT_READY"
  tail -40 /var/lib/zenui/visualizer-chrome.log 2>/dev/null || true
  exit 41
fi

if runuser -u zenui -- env DISPLAY=:0 /usr/local/bin/zen-control-room-layout; then
  echo "LAYOUT_APPLY=PASS"
else
  echo "LAYOUT_APPLY=FAIL"
  exit 42
fi

echo "=== WINDOWS_AFTER ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lxG 2>/dev/null || true

echo "=== HEALTH ==="
curl -fsS --max-time 4 http://127.0.0.1:18992/health
echo

echo "RESULT=PASS"
