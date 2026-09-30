#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
xsetroot -solid '#1b1a18' || true
xhost +SI:localuser:zenui >/dev/null 2>&1 || true

output="$(runuser -u zenui -- env DISPLAY=:0 /usr/bin/xrandr --query | awk '/ connected/{print $1; exit}')"
if [[ -n "$output" ]]; then
  runuser -u zenui -- env DISPLAY=:0 /usr/bin/xrandr --output "$output" --rotate inverted || true
fi

exec runuser -u zenui -- env \
  HOME=/var/lib/zenui \
  USER=zenui \
  LOGNAME=zenui \
  DISPLAY=:0 \
  XDG_SESSION_TYPE=x11 \
  XDG_CONFIG_HOME=/var/lib/zenui/.config \
  dbus-run-session -- bash -lc '
    set -u
    openbox-session >/var/lib/zenui/openbox.log 2>&1 &
    sleep 1

    /usr/bin/chatgpt >/var/lib/zenui/chatgpt-gui.log 2>&1 &
    CHATGPT_PID=$!

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

    for _ in $(seq 1 20); do
      if /usr/local/bin/zen-control-room-layout living >/var/lib/zenui/control-room-layout.log 2>&1; then
        break
      fi
      sleep 0.5
    done

    wait "$CHATGPT_PID"
  '
