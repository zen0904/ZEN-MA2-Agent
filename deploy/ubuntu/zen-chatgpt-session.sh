#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
xsetroot -solid '#202124' || true
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

    for _ in $(seq 1 20); do
      if /usr/bin/curl -fsS --max-time 1 http://127.0.0.1:18992/health >/dev/null 2>&1; then
        break
      fi
      sleep 0.5
    done

    /usr/bin/google-chrome \
      --app=http://127.0.0.1:18992/ \
      --user-data-dir=/var/lib/zenui/.config/zen-living-chrome \
      --no-first-run \
      --disable-session-crashed-bubble \
      --disable-features=Translate \
      --ozone-platform=x11 \
      >/var/lib/zenui/visualizer-chrome.log 2>&1 &

    for _ in $(seq 1 12); do
      if /usr/local/bin/zen-control-room-layout >/var/lib/zenui/control-room-layout.log 2>&1; then
        break
      fi
      sleep 1
    done

    wait "$CHATGPT_PID"
  '
