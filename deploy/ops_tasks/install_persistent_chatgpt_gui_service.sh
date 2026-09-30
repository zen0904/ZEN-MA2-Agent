#!/usr/bin/env bash
set -euo pipefail

SERVICE=/etc/systemd/system/zen-chatgpt-gui.service
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
ExecStartPre=/bin/bash -lc 'if pgrep -f "/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0" >/dev/null 2>&1; then exit 0; fi; rm -f /tmp/.X0-lock /tmp/.X11-unix/X0'
ExecStart=/usr/bin/xinit /usr/local/libexec/zen-chatgpt-session.sh -- /usr/bin/Xorg :0 vt3 -nolisten tcp -noreset
ExecStartPost=/bin/bash -lc 'sleep 3; /usr/bin/chvt 3 || true'
Restart=always
RestartSec=3
KillMode=control-group
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF

# A previous systemd-run session may have created the exact same unit name as
# a transient unit under /run. Remove that transient registration before
# daemon-reload so the persistent /etc unit becomes authoritative.
systemctl stop zen-chatgpt-gui.service >/dev/null 2>&1 || true
rm -f /run/systemd/transient/zen-chatgpt-gui.service
systemctl reset-failed zen-chatgpt-gui.service >/dev/null 2>&1 || true
systemctl daemon-reload

# Chrome was only a login handoff helper. Keep it available, but do not launch
# it automatically at every boot now that ChatGPT owns the persistent GUI.
systemctl disable zen-mini-chrome.service >/dev/null 2>&1 || true
systemctl stop zen-mini-chrome.service >/dev/null 2>&1 || true

# Replace any previous transient ChatGPT/Xorg unit with the durable service.
mapfile -t transient_units < <(
  systemctl list-units 'zen-chatgpt-gui*.service' --all --no-legend 2>/dev/null |
  awk '{print $1}' |
  grep -v '^zen-chatgpt-gui\.service
for unit in "${transient_units[@]}"; do
  systemctl stop "$unit" >/dev/null 2>&1 || true
done

# Clear stale X locks only after old GUI units are stopped.
if ! pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' >/dev/null 2>&1; then
  rm -f /tmp/.X0-lock /tmp/.X11-unix/X0
fi

systemctl enable --now zen-chatgpt-gui.service

# The taskbar attaches to display :0. Keep it enabled and restart once the new
# X server is ready so it always follows ChatGPT at boot.
systemctl enable zen-mini-taskbar.service >/dev/null 2>&1 || true
for _ in $(seq 1 60); do
  [[ -S /tmp/.X11-unix/X0 ]] && break
  sleep 1
done
[[ -S /tmp/.X11-unix/X0 ]]
systemctl restart zen-mini-taskbar.service || true
chvt 3 || true
sleep 5

echo "CHATGPT_GUI_ACTIVE=$(systemctl is-active zen-chatgpt-gui.service || true)"
echo "CHATGPT_GUI_ENABLED=$(systemctl is-enabled zen-chatgpt-gui.service || true)"
echo "CHATGPT_PROCESS=$(pgrep -u zenui -f '/usr/bin/chatgpt|/usr/lib/chatgpt' | head -1 || true)"
echo "XORG_PROCESS=$(pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' | head -1 || true)"
echo "TASKBAR_ACTIVE=$(systemctl is-active zen-mini-taskbar.service || true)"
echo "CHROME_ENABLED=$(systemctl is-enabled zen-mini-chrome.service 2>/dev/null || true)"
echo "CHROME_ACTIVE=$(systemctl is-active zen-mini-chrome.service 2>/dev/null || true)"
echo "PERSISTENT_CHATGPT_GUI=PASS"
 || true
)
for unit in "${transient_units[@]}"; do
  systemctl stop "$unit" >/dev/null 2>&1 || true
done

# Clear stale X locks only after old GUI units are stopped.
if ! pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' >/dev/null 2>&1; then
  rm -f /tmp/.X0-lock /tmp/.X11-unix/X0
fi

systemctl enable --now zen-chatgpt-gui.service

# The taskbar attaches to display :0. Keep it enabled and restart once the new
# X server is ready so it always follows ChatGPT at boot.
systemctl enable zen-mini-taskbar.service >/dev/null 2>&1 || true
for _ in $(seq 1 60); do
  [[ -S /tmp/.X11-unix/X0 ]] && break
  sleep 1
done
[[ -S /tmp/.X11-unix/X0 ]]
systemctl restart zen-mini-taskbar.service || true
chvt 3 || true
sleep 5

echo "CHATGPT_GUI_ACTIVE=$(systemctl is-active zen-chatgpt-gui.service || true)"
echo "CHATGPT_GUI_ENABLED=$(systemctl is-enabled zen-chatgpt-gui.service || true)"
echo "CHATGPT_PROCESS=$(pgrep -u zenui -f '/usr/bin/chatgpt|/usr/lib/chatgpt' | head -1 || true)"
echo "XORG_PROCESS=$(pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' | head -1 || true)"
echo "TASKBAR_ACTIVE=$(systemctl is-active zen-mini-taskbar.service || true)"
echo "CHROME_ENABLED=$(systemctl is-enabled zen-mini-chrome.service 2>/dev/null || true)"
echo "CHROME_ACTIVE=$(systemctl is-active zen-mini-chrome.service 2>/dev/null || true)"
echo "PERSISTENT_CHATGPT_GUI=PASS"
