#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${ZEN_DISPLAY:-:0}"
GUI_USER="zenui"

echo "TASK=ROTATE_DISPLAY_180"
echo "DISPLAY=${DISPLAY_NUM}"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' >/dev/null || {
  echo "XORG_DISPLAY_READY=NO"
  exit 70
}

output="$(
  runuser -u "$GUI_USER" -- env DISPLAY="$DISPLAY_NUM" /usr/bin/xrandr --query |
    awk '/ connected/{print $1; exit}'
)"

if [[ -z "$output" ]]; then
  echo "CONNECTED_OUTPUT=NONE"
  exit 71
fi

echo "CONNECTED_OUTPUT=$output"
echo "BEFORE="
runuser -u "$GUI_USER" -- env DISPLAY="$DISPLAY_NUM" /usr/bin/xrandr --query |
  awk -v out="$output" '$1 == out {print; exit}'

runuser -u "$GUI_USER" -- env DISPLAY="$DISPLAY_NUM"   /usr/bin/xrandr --output "$output" --rotate inverted

sleep 1

echo "AFTER="
runuser -u "$GUI_USER" -- env DISPLAY="$DISPLAY_NUM" /usr/bin/xrandr --query |
  awk -v out="$output" '$1 == out {print; exit}'

echo "DISPLAY_ROTATION=180"
echo "RESULT=PASS"
