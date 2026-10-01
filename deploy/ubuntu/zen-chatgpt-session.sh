#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
xsetroot -solid '#1b1a18' || true
xhost +SI:localuser:zenui >/dev/null 2>&1 || true
xhost +SI:localuser:zengw >/dev/null 2>&1 || true

output="$(runuser -u zenui -- env DISPLAY=:0 /usr/bin/xrandr --query | awk '/ connected/{print $1; exit}')"
if [[ -n "$output" ]]; then
  runuser -u zenui -- env DISPLAY=:0 /usr/bin/xrandr --output "$output" --rotate inverted || true
fi

exec runuser -u zenui -- env   HOME=/var/lib/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_SESSION_TYPE=x11   XDG_CONFIG_HOME=/var/lib/zenui/.config   dbus-run-session -- bash -lc '
    set -u
    openbox-session >/var/lib/zenui/openbox.log 2>&1 &
    sleep 1

    /usr/bin/chatgpt >/var/lib/zenui/chatgpt-gui.log 2>&1 &
    CHATGPT_PID=$!

    wait "$CHATGPT_PID"
  '
