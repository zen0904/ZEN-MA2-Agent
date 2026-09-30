#!/usr/bin/env bash
set -euo pipefail

UNIT=zen-codex-device-auth.service
CODEX=/usr/local/bin/codex

[[ -x "$CODEX" ]] || { echo "CODEX_MISSING"; exit 70; }
[[ -c /dev/tty2 ]] || { echo "TTY2_MISSING"; exit 71; }

systemctl stop "$UNIT" >/dev/null 2>&1 || true
systemctl reset-failed "$UNIT" >/dev/null 2>&1 || true

systemd-run   --unit=zen-codex-device-auth   --property=Type=simple   --property=StandardInput=tty-force   --property=StandardOutput=tty   --property=StandardError=tty   --property=TTYPath=/dev/tty2   --property=TTYReset=yes   --property=TTYVHangup=yes   --property=TTYVTDisallocate=yes   --setenv=HOME=/root   --setenv=PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin   "$CODEX" login --device-auth >/dev/null

sleep 1
chvt 2
sleep 1

echo "CODEX_DEVICE_AUTH_SERVICE=$(systemctl is-active "$UNIT" 2>/dev/null || true)"
echo "CONSOLE_VT=2"
echo "DEVICE_AUTH_VISIBLE_ON_LOCAL_CONSOLE=YES"
echo "DEVICE_CODE_EXPOSED_TO_OPS=NO"
