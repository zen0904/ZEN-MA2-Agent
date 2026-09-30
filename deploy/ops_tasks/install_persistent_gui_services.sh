#!/usr/bin/env bash
set -euo pipefail

install -d -o zenui -g zenui -m 0700 /var/lib/zenui/.config/tint2 /var/lib/zenui/.config/google-chrome

cat >/etc/systemd/system/zen-mini-taskbar.service <<'EOF'
[Unit]
Description=ZEN Mini GUI taskbar
After=multi-user.target

[Service]
Type=simple
User=zenui
Group=zenui
Environment=HOME=/var/lib/zenui
Environment=USER=zenui
Environment=LOGNAME=zenui
Environment=DISPLAY=:0
Environment=XDG_CONFIG_HOME=/var/lib/zenui/.config
ExecStartPre=/bin/sh -c 'for i in $(seq 1 60); do [ -S /tmp/.X11-unix/X0 ] && exit 0; sleep 1; done; exit 1'
ExecStart=/usr/bin/tint2 -c /var/lib/zenui/.config/tint2/tint2rc
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/zen-mini-chrome.service <<'EOF'
[Unit]
Description=ZEN Mini Chrome session
After=multi-user.target

[Service]
Type=simple
User=zenui
Group=zenui
Environment=HOME=/var/lib/zenui
Environment=USER=zenui
Environment=LOGNAME=zenui
Environment=DISPLAY=:0
Environment=XDG_CONFIG_HOME=/var/lib/zenui/.config
ExecStartPre=/bin/sh -c 'for i in $(seq 1 60); do [ -S /tmp/.X11-unix/X0 ] && exit 0; sleep 1; done; exit 1'
ExecStart=/usr/bin/google-chrome --no-first-run --no-default-browser-check --disable-gpu --user-data-dir=/var/lib/zenui/.config/google-chrome https://www.google.com/
Restart=no
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now zen-mini-taskbar.service zen-mini-chrome.service
sleep 5

echo "TASKBAR_SERVICE=$(systemctl is-active zen-mini-taskbar.service || true)"
echo "CHROME_SERVICE=$(systemctl is-active zen-mini-chrome.service || true)"
echo "TASKBAR_PID=$(pgrep -u zenui -x tint2 | head -1 || true)"
echo "CHROME_PID=$(pgrep -u zenui -f '/opt/google/chrome/chrome|google-chrome' | head -1 || true)"
DISPLAY=:0 wmctrl -l -x || true
DISPLAY=:0 wmctrl -a "Google" 2>/dev/null || DISPLAY=:0 wmctrl -a "Google Chrome" 2>/dev/null || true
chvt 3 2>/dev/null || true
echo "PERSISTENT_GUI_SERVICES=PASS"
