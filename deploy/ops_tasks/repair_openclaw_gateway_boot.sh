#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PORT=18789
TARGET=openclaw-gateway.service

echo "=== root linger ==="
loginctl enable-linger root
linger="$(loginctl show-user root -p Linger --value 2>/dev/null || true)"
echo "LINGER=${linger:-unknown}"

echo "=== ensure root user manager ==="
systemctl start user@0.service
user_bus=NO
for _ in $(seq 1 20); do
  if systemctl --user show-environment >/dev/null 2>&1; then
    user_bus=YES
    break
  fi
  sleep 0.25
done
echo "ROOT_USER_BUS=${user_bus}"

if [[ "$user_bus" == YES ]]; then
  echo "=== managed user-unit repair ==="
  units="$(systemctl --user list-unit-files --type=service --no-legend 2>/dev/null | awk '$1 ~ /^openclaw/ {print $1}')"
  [[ -n "$units" ]] || { echo "OPENCLAW_USER_UNIT=MISSING"; exit 20; }
  printf '%s\n' "$units"
  target="$(printf '%s\n' "$units" | grep -E '^openclaw-gateway(\.service|-.*\.service)$' | head -1 || true)"
  [[ -n "$target" ]] || target="$(printf '%s\n' "$units" | head -1)"
  TARGET="$target"
  echo "OPENCLAW_TARGET_UNIT=$TARGET"
  systemctl --user daemon-reload
  systemctl --user enable "$TARGET" >/dev/null
  systemctl --user restart "$TARGET"
  systemctl --user is-enabled "$TARGET"
  systemctl --user is-active "$TARGET"
else
  echo "=== filesystem/cgroup persistence verification ==="
  unit_found=NO
  enabled_link=NO
  active_cgroup=NO
  if find /root/.config/systemd/user /etc/systemd/user /usr/lib/systemd/user \
      -maxdepth 4 -type f -name "$TARGET" -print -quit 2>/dev/null | grep -q .; then
    unit_found=YES
  fi
  if find /root/.config/systemd/user /etc/systemd/user \
      -maxdepth 5 -type l -name "$TARGET" -print -quit 2>/dev/null | grep -q .; then
    enabled_link=YES
  fi
  for cg in /proc/[0-9]*/cgroup; do
    if grep -q '/openclaw-gateway.service$' "$cg" 2>/dev/null; then
      active_cgroup=YES
      break
    fi
  done
  echo "OPENCLAW_UNIT_FILE=${unit_found}"
  echo "OPENCLAW_ENABLE_LINK=${enabled_link}"
  echo "OPENCLAW_ACTIVE_CGROUP=${active_cgroup}"
  if [[ "$linger" != yes || "$unit_found" != YES || "$enabled_link" != YES || "$active_cgroup" != YES ]]; then
    echo "OPENCLAW_BOOT_PERSISTENCE=UNVERIFIED"
    exit 21
  fi
fi

echo "=== gateway listener ==="
for _ in $(seq 1 40); do
  if ss -ltn 2>/dev/null | grep -qE "127\\.0\\.0\\.1:${PORT}[[:space:]]"; then
    break
  fi
  sleep 0.25
done
if ! ss -ltn 2>/dev/null | grep -E "127\\.0\\.0\\.1:${PORT}[[:space:]]"; then
  echo "OPENCLAW_PORT=NOT_LISTENING"
  exit 22
fi

echo "=== daemon status ==="
/opt/node/bin/openclaw daemon status --json 2>&1 | sed -E 's/(token|password|secret)([=: ][^ ]+)/\1=[REDACTED]/Ig' | head -120 || true

echo "OPENCLAW_GATEWAY=ACTIVE"
echo "OPENCLAW_PORT=LISTEN"
echo "OPENCLAW_BOOT_PERSISTENCE=RESTORED"
