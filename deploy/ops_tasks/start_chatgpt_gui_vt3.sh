#!/usr/bin/env bash
set -euo pipefail

UNIT=zen-chatgpt-gui.service
DISPLAY_NUM=:0
VT=3

systemctl stop "$UNIT" >/dev/null 2>&1 || true
pkill -f '/usr/lib/xorg/Xorg :0' >/dev/null 2>&1 || true
rm -f /tmp/.X0-lock
rm -f /tmp/.X11-unix/X0

systemd-run   --unit=zen-chatgpt-gui   --property=Type=simple   --property=Restart=no   /usr/bin/xinit /usr/local/libexec/zen-chatgpt-session.sh --   /usr/bin/Xorg "$DISPLAY_NUM" "vt$VT" -nolisten tcp -noreset >/dev/null

for _ in $(seq 1 30); do
  [[ -S /tmp/.X11-unix/X0 ]] && break
  sleep 0.5
done

[[ -S /tmp/.X11-unix/X0 ]] || {
  echo "XORG_DISPLAY_READY=NO"
  systemctl status "$UNIT" --no-pager -n 30 || true
  exit 72
}

chvt "$VT"
sleep 4

echo "XORG_DISPLAY_READY=YES"
echo "CONSOLE_VT=$VT"
echo "CHATGPT_GUI_SERVICE=$(systemctl is-active "$UNIT" 2>/dev/null || true)"
if pgrep -u zenui -f '/usr/bin/chatgpt|/usr/lib/chatgpt' >/dev/null 2>&1; then
  echo "CHATGPT_PROCESS=RUNNING"
else
  echo "CHATGPT_PROCESS=NOT_FOUND"
  systemctl status "$UNIT" --no-pager -n 40 || true
  exit 73
fi
echo "CHATGPT_LOGIN_UI=VISIBLE_ON_MINI"
