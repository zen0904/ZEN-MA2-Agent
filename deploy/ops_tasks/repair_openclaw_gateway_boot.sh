#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PORT=18789

echo "=== root linger ==="
loginctl enable-linger root
loginctl show-user root -p Linger -p State -p RuntimePath 2>/dev/null || true

echo "=== ensure root user manager ==="
systemctl start user@0.service
for _ in $(seq 1 40); do
  if [[ -S /run/user/0/bus ]] && systemctl --user show-environment >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
if ! [[ -S /run/user/0/bus ]] || ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "ROOT_USER_MANAGER=UNREACHABLE"
  systemctl status user@0.service --no-pager --lines=20 2>&1 || true
  ls -la /run/user/0 2>/dev/null || true
  exit 21
fi
echo "ROOT_USER_MANAGER=REACHABLE"

echo "=== existing OpenClaw user units ==="
units="$(systemctl --user list-unit-files --type=service --no-legend 2>/dev/null | awk '$1 ~ /^openclaw/ {print $1}')"
if [[ -z "$units" ]]; then
  echo "OPENCLAW_USER_UNIT=MISSING"
  exit 20
fi
printf '%s\n' "$units"

target="$(printf '%s\n' "$units" | grep -E '^openclaw-gateway(\.service|-.*\.service)$' | head -1 || true)"
if [[ -z "$target" ]]; then
  target="$(printf '%s\n' "$units" | head -1)"
fi

echo "OPENCLAW_TARGET_UNIT=$target"
systemctl --user daemon-reload
systemctl --user enable "$target" >/dev/null
systemctl --user restart "$target"

echo "=== service state ==="
systemctl --user show "$target" \
  -p LoadState -p ActiveState -p SubState -p UnitFileState -p FragmentPath \
  --no-pager
systemctl --user is-enabled "$target"
systemctl --user is-active "$target"

echo "=== gateway listener ==="
for _ in $(seq 1 60); do
  if ss -ltn 2>/dev/null | grep -qE "127\\.0\\.0\\.1:${PORT}[[:space:]]"; then
    break
  fi
  sleep 0.25
done
if ! ss -ltn 2>/dev/null | grep -E "127\\.0\\.0\\.1:${PORT}[[:space:]]"; then
  echo "OPENCLAW_PORT=NOT_LISTENING"
  systemctl --user status "$target" --no-pager --lines=40 2>&1 | sed -E 's/(token|password|secret)([=: ][^ ]+)/\1=[REDACTED]/Ig' || true
  exit 22
fi

echo "=== daemon status ==="
/opt/node/bin/openclaw daemon status --json 2>&1 | sed -E 's/(token|password|secret)([=: ][^ ]+)/\1=[REDACTED]/Ig' | head -120 || true

echo "OPENCLAW_GATEWAY=ACTIVE"
echo "OPENCLAW_PORT=LISTEN"
echo "OPENCLAW_BOOT_PERSISTENCE=RESTORED"
