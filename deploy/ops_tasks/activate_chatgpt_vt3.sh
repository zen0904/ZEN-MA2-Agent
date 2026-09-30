#!/usr/bin/env bash
set -euo pipefail

if ! pgrep -u zenui -f "/usr/bin/chatgpt|/usr/lib/chatgpt" >/dev/null 2>&1; then
  echo "CHATGPT_PROCESS=NOT_RUNNING"
  exit 70
fi
chvt 3
sleep 1
echo "CHATGPT_PROCESS=RUNNING"
echo "CONSOLE_SWITCHED_TO_VT3=YES"
echo "CHATGPT_LOGIN_UI_READY=YES"
