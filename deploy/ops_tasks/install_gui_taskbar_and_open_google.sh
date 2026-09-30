#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends tint2

install -d -o zenui -g zenui -m 0700 /var/lib/zenui/.config/tint2
cat >/var/lib/zenui/.config/tint2/tint2rc <<'EOF'
panel_items = T
panel_position = bottom center horizontal
panel_size = 100% 42
panel_margin = 0 0
panel_padding = 8 4 8
panel_background_id = 0
wm_menu = 1
taskbar_mode = single_desktop
taskbar_padding = 4 2 4
taskbar_background_id = 0
task_icon = 1
task_text = 1
task_centered = 0
task_maximum_size = 220 36
task_padding = 8 4 8
task_font = Sans 11
task_font_color = #ffffff 100
task_active_font_color = #ffffff 100
task_background_id = 0
task_active_background_id = 0
background_color = #202124 92
border_width = 0
corner_radius = 0
EOF
chown -R zenui:zenui /var/lib/zenui/.config/tint2

pkill -u zenui -x tint2 >/dev/null 2>&1 || true
setsid runuser -u zenui -- env HOME=/var/lib/zenui DISPLAY=:0 XDG_CONFIG_HOME=/var/lib/zenui/.config tint2 -c /var/lib/zenui/.config/tint2/tint2rc >/var/lib/zenui/tint2.log 2>&1 </dev/null &

if ! pgrep -u zenui -f "/opt/google/chrome/chrome|google-chrome" >/dev/null 2>&1; then
  setsid runuser -u zenui -- env HOME=/var/lib/zenui USER=zenui LOGNAME=zenui DISPLAY=:0 XDG_CONFIG_HOME=/var/lib/zenui/.config /usr/bin/google-chrome --no-first-run --no-default-browser-check --disable-gpu https://www.google.com/ >/var/lib/zenui/chrome.log 2>&1 </dev/null &
else
  runuser -u zenui -- env HOME=/var/lib/zenui DISPLAY=:0 /usr/bin/google-chrome https://www.google.com/ >/dev/null 2>&1 || true
fi

sleep 3
chvt 3 2>/dev/null || true
echo "TINT2=$(pgrep -u zenui -x tint2 >/dev/null && echo RUNNING || echo NOT_RUNNING)"
echo "CHROME=$(pgrep -u zenui -f "/opt/google/chrome/chrome|google-chrome" >/dev/null && echo RUNNING || echo NOT_RUNNING)"
echo "CHATGPT=$(pgrep -u zenui -f "/usr/lib/chatgpt/ChatGPT" >/dev/null && echo RUNNING || echo NOT_RUNNING)"
echo "APP_SWITCHER_READY=YES"
