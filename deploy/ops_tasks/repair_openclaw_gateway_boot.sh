#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
unset DBUS_SESSION_BUS_ADDRESS || true
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo "=== root linger ==="
loginctl enable-linger root
loginctl show-user root -p Linger -p State -p RuntimePath 2>/dev/null || true

echo "=== ensure root user manager ==="
systemctl start user@0.service
for _ in $(seq 1 20); do
  if systemctl --user --machine=root@.host show-environment >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
if ! systemctl --user --machine=root@.host show-environment >/dev/null 2>&1; then
  echo "ROOT_USER_MANAGER=UNREACHABLE"
  systemctl status user@0.service --no-pager --lines=20 2>&1 || true
  ls -la /run/user/0 2>/dev/null || true
  exit 21
fi
echo "ROOT_USER_MANAGER=REACHABLE"

echo "=== existing OpenClaw user units ==="
units="$(systemctl --user --machine=root@.host list-unit-files --type=service --no-legend 2>/dev/null | awk '$1 ~ /^openclaw/ {print $1}')"
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
systemctl --user --machine=root@.host daemon-reload
systemctl --user --machine=root@.host enable "$target" >/dev/null
systemctl --user --machine=root@.host restart "$target"

echo "=== service state ==="
systemctl --user --machine=root@.host show "$target" \
  -p LoadState -p ActiveState -p SubState -p UnitFileState -p FragmentPath \
  --no-pager

echo "=== gateway listener ==="
for _ in $(seq 1 40); do
  if ss -ltn 2>/dev/null | grep -q ':18789 '; then
    break
  fi
  sleep 0.25
done
ss -ltn 2>/dev/null | grep ':18789 ' || true

echo "=== gateway health ==="
if curl -fsS --max-time 5 http://127.0.0.1:18789/healthz >/tmp/openclaw-health.$$ 2>/dev/null; then
  echo "OPENCLAW_HEALTH=OK"
  head -c 500 /tmp/openclaw-health.$$ || true
  echo
else
  echo "OPENCLAW_HEALTH=FAILED"
  systemctl --user --machine=root@.host status "$target" --no-pager --lines=20 2>&1 | sed -E 's/(token|password|secret)=([^ ]+)/\1=REDACTED/Ig' || true
  rm -f /tmp/openclaw-health.$$
  exit 22
fi
rm -f /tmp/openclaw-health.$$

echo "OPENCLAW_BOOT_PERSISTENCE=RESTORED"
