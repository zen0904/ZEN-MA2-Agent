#!/usr/bin/env bash
set -euo pipefail

SERVICE=/etc/systemd/system/zen-chatgpt-desktop.service
SESSION=/usr/local/libexec/zen-chatgpt-session.sh

echo "TASK=INSTALL_PERSISTENT_CHATGPT_GUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -x /usr/bin/chatgpt
test -x "$SESSION"

cat >"$SERVICE" <<'EOF'
[Unit]
Description=ZEN Mini persistent ChatGPT GUI on VT3
After=network-online.target systemd-user-sessions.service
Wants=network-online.target
Conflicts=getty@tty3.service

[Service]
Type=simple
ExecStart=/usr/bin/xinit /usr/local/libexec/zen-chatgpt-session.sh -- /usr/bin/Xorg :0 vt3 -nolisten tcp -noreset
ExecStartPost=/bin/bash -lc 'sleep 3; /usr/bin/chvt 3 || true'
Restart=always
RestartSec=3
KillMode=control-group
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF

# Retire every old transient ChatGPT GUI unit before the persistent service
# takes ownership of display :0 and VT3.
mapfile -t old_units < <(
  systemctl list-units 'zen-chatgpt-gui*.service' --all --no-legend 2>/dev/null |
  awk '{print $1}' || true
)
for unit in "${old_units[@]}"; do
  systemctl stop "$unit" >/dev/null 2>&1 || true
done

systemctl stop zen-chatgpt-desktop.service >/dev/null 2>&1 || true
rm -f /run/systemd/transient/zen-chatgpt-desktop.service
rm -f /run/systemd/transient/zen-chatgpt-gui.service
systemctl reset-failed zen-chatgpt-desktop.service >/dev/null 2>&1 || true

# Chrome was only the browser handoff used for login. Leave it installed, but
# do not launch it automatically once the native ChatGPT GUI is persistent.
systemctl disable zen-mini-chrome.service >/dev/null 2>&1 || true
systemctl stop zen-mini-chrome.service >/dev/null 2>&1 || true

# Display :0 is dedicated to this Mini GUI. Clear any orphan from the old
# transient session so xinit can claim the display cleanly.
if pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' >/dev/null 2>&1; then
  pkill -TERM -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do
    pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' >/dev/null 2>&1 || break
    sleep 0.5
  done
fi
rm -f /tmp/.X0-lock /tmp/.X11-unix/X0

systemctl daemon-reload
systemctl enable --now zen-chatgpt-desktop.service

# Wait for the new X server and ChatGPT process.
for _ in $(seq 1 60); do
  [[ -S /tmp/.X11-unix/X0 ]] && break
  sleep 1
done
[[ -S /tmp/.X11-unix/X0 ]]

for _ in $(seq 1 60); do
  pgrep -u zenui -f '/usr/bin/chatgpt|/usr/lib/chatgpt' >/dev/null 2>&1 && break
  sleep 1
done
pgrep -u zenui -f '/usr/bin/chatgpt|/usr/lib/chatgpt' >/dev/null 2>&1

# Keep the existing taskbar attached to the new display.
systemctl enable zen-mini-taskbar.service >/dev/null 2>&1 || true
systemctl restart zen-mini-taskbar.service || true
chvt 3 || true
sleep 3

echo "CHATGPT_GUI_ACTIVE=$(systemctl is-active zen-chatgpt-desktop.service || true)"
echo "CHATGPT_GUI_ENABLED=$(systemctl is-enabled zen-chatgpt-desktop.service || true)"
echo "CHATGPT_PROCESS=$(pgrep -u zenui -f '/usr/bin/chatgpt|/usr/lib/chatgpt' | head -1 || true)"
echo "XORG_PROCESS=$(pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' | head -1 || true)"
echo "TASKBAR_ACTIVE=$(systemctl is-active zen-mini-taskbar.service || true)"
echo "CHROME_ENABLED=$(systemctl is-enabled zen-mini-chrome.service 2>/dev/null || true)"
echo "CHROME_ACTIVE=$(systemctl is-active zen-mini-chrome.service 2>/dev/null || true)"
echo "PERSISTENT_CHATGPT_GUI=PASS"
