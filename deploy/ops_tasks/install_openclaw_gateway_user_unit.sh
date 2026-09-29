#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
OPENCLAW=/opt/node/bin/openclaw
PORT=18789
UNIT_DIR=/root/.config/systemd/user
UNIT=${UNIT_DIR}/openclaw-gateway.service
WANTS=${UNIT_DIR}/default.target.wants
LINK=${WANTS}/openclaw-gateway.service
STATUS=/var/lib/zen-ops/openclaw-persistence-status.txt

exec > >(tee "$STATUS") 2>&1

[[ -x "$OPENCLAW" ]] || { echo "OPENCLAW_BINARY=MISSING"; exit 31; }

echo "=== root user persistence ==="
loginctl enable-linger root
linger="$(loginctl show-user root -p Linger --value 2>/dev/null || true)"
echo "LINGER=${linger:-unknown}"
[[ "$linger" == yes ]] || { echo "LINGER_ENABLE=FAILED"; exit 21; }

install -d -m 0700 "$UNIT_DIR" "$WANTS"

if [[ ! -f "$UNIT" ]]; then
  tmp="$(mktemp)"
  cat >"$tmp" <<EOF
[Unit]
Description=OpenClaw Gateway (ZEN managed persistent user unit)
After=network-online.target
Wants=network-online.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
Environment=HOME=/root
Environment=PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/node/bin/openclaw gateway --port ${PORT}
Restart=always
RestartSec=5
RestartPreventExitStatus=78
TimeoutStopSec=30
TimeoutStartSec=30
SuccessExitStatus=0 143
OOMPolicy=continue
KillMode=control-group

[Install]
WantedBy=default.target
EOF
  install -m 0644 "$tmp" "$UNIT"
  rm -f "$tmp"
  echo "PERSISTENT_UNIT_CREATED=YES"
else
  echo "PERSISTENT_UNIT_CREATED=NO"
fi

if ! grep -qF "ExecStart=/opt/node/bin/openclaw gateway --port ${PORT}" "$UNIT"; then
  echo "PERSISTENT_UNIT_UNEXPECTED_EXECSTART"
  exit 23
fi
if ! grep -qF 'WantedBy=default.target' "$UNIT"; then
  echo "PERSISTENT_UNIT_UNEXPECTED_INSTALL_TARGET"
  exit 24
fi

ln -sfn ../openclaw-gateway.service "$LINK"
systemd-analyze verify "$UNIT" >/tmp/zen-openclaw-unit-verify.$$ 2>&1 || {
  cat /tmp/zen-openclaw-unit-verify.$$
  rm -f /tmp/zen-openclaw-unit-verify.$$
  exit 25
}
rm -f /tmp/zen-openclaw-unit-verify.$$
echo "OPENCLAW_UNIT_VERIFY=PASS"
[[ -L "$LINK" ]] || { echo "OPENCLAW_ENABLE_LINK=NO"; exit 26; }
echo "OPENCLAW_ENABLE_LINK=YES"

active_cgroup=NO
for cg in /proc/[0-9]*/cgroup; do
  if grep -q '/openclaw-gateway.service$' "$cg" 2>/dev/null; then
    active_cgroup=YES
    break
  fi
done
echo "OPENCLAW_ACTIVE_CGROUP=${active_cgroup}"
[[ "$active_cgroup" == YES ]] || exit 27

if ! ss -ltn 2>/dev/null | grep -qE "127\\.0\\.0\\.1:${PORT}[[:space:]]"; then
  echo "OPENCLAW_PORT=NOT_LISTENING"
  exit 28
fi
echo "OPENCLAW_PORT=LISTEN"
"$OPENCLAW" --version

echo "OPENCLAW_BOOT_PERSISTENCE=CONFIGURED"
echo "REBOOT_VERIFICATION=PENDING"
