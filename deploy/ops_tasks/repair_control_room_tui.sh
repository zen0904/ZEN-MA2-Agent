#!/usr/bin/env bash
set -euo pipefail

echo "TASK=REPAIR_CONTROL_ROOM_TUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

export DISPLAY=:0

# Close only the legacy Visualizer Chrome app window. Do not touch unrelated Chrome.
while read -r id; do
  [[ -n "$id" ]] && runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -i -c "$id" >/dev/null 2>&1 || true
done < <(runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>/dev/null |
  awk 'tolower($0) ~ /google-chrome/ && tolower($0) ~ /zen living system/ {print $1}')

windows="$(runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>/dev/null || true)"
if ! printf '%s\n' "$windows" | grep -qi 'zen-living-tui\|zen living workspace'; then
  runuser -u zenui -- env \
    HOME=/var/lib/zenui \
    USER=zenui \
    LOGNAME=zenui \
    DISPLAY=:0 \
    TERM=xterm-256color \
    /usr/bin/xterm \
      -T "ZEN Living Workspace" \
      -name zen-living-tui \
      -fa "DejaVu Sans Mono" \
      -fs 10 \
      -bg "#1b1a18" \
      -fg "#e9e1d8" \
      -bd "#1b1a18" \
      -cr "#c7b8a3" \
      +sb \
      -b 0 \
      -e /usr/local/bin/zen-living-tui \
      >/var/lib/zenui/living-tui-xterm.log 2>&1 &
  echo "TUI_LAUNCH=STARTED"
else
  echo "TUI_LAUNCH=ALREADY_PRESENT"
fi

ready=0
for _ in $(seq 1 20); do
  windows="$(runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lx 2>/dev/null || true)"
  if printf '%s\n' "$windows" | grep -qi 'zen-living-tui\|zen living workspace'; then
    ready=1
    break
  fi
  sleep 0.5
done

if [[ "$ready" != "1" ]]; then
  echo "TUI_WINDOW=NOT_READY"
  tail -60 /var/lib/zenui/living-tui-xterm.log 2>/dev/null || true
  exit 41
fi

runuser -u zenui -- env DISPLAY=:0 /usr/local/bin/zen-control-room-layout living

echo "=== WINDOWS_AFTER ==="
runuser -u zenui -- env DISPLAY=:0 /usr/bin/wmctrl -lxG 2>/dev/null || true

echo "=== TUI_PROCESS ==="
pgrep -a -u zenui -f '/usr/local/bin/zen-living-tui' || true

echo "=== WEB_VISUALIZER ==="
systemctl is-active zen-living-visualizer.service 2>/dev/null || true

echo "RESULT=PASS"
