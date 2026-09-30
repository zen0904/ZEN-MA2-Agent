#!/usr/bin/env bash
set -euo pipefail

install -d -o zenui -g zenui -m 0700 /var/lib/zenui/.config/google-chrome
pkill -u zenui -f "/usr/bin/google-chrome|/opt/google/chrome/chrome" >/dev/null 2>&1 || true

setsid runuser -u zenui -- env \
  HOME=/var/lib/zenui \
  USER=zenui \
  LOGNAME=zenui \
  DISPLAY=:0 \
  XDG_CONFIG_HOME=/var/lib/zenui/.config \
  /usr/bin/google-chrome \
    --no-first-run \
    --no-default-browser-check \
    --disable-gpu \
    https://chatgpt.com/ \
  >/var/lib/zenui/chrome.log 2>&1 </dev/null &

for _ in $(seq 1 30); do
  if pgrep -u zenui -f "/opt/google/chrome/chrome|google-chrome" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! pgrep -u zenui -f "/opt/google/chrome/chrome|google-chrome" >/dev/null 2>&1; then
  echo "CHROME_PROCESS=NOT_RUNNING"
  tail -n 80 /var/lib/zenui/chrome.log 2>/dev/null || true
  exit 70
fi

chvt 3 2>/dev/null || true
echo "CHROME_PROCESS=RUNNING"
echo "CHROME_URL=https://chatgpt.com/"
echo "CONSOLE_VT=3"
echo "CHROME_VISIBLE_ON_MINI=YES"
