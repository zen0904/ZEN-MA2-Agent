#!/usr/bin/env bash
set -euo pipefail

RUNTIME=/opt/zen/zen-ops-runtime
HELPER=${RUNTIME}/deploy/ops_tasks/install_openclaw_gateway_user_unit.sh
SYSTEM_UNIT=/etc/systemd/system/zen-openclaw-persistence-repair.service
STATUS=/var/lib/zen-ops/openclaw-persistence-status.txt

[[ -f "$HELPER" ]] || { echo "OPENCLAW_PERSISTENCE_HELPER=MISSING"; exit 31; }

cat >"$SYSTEM_UNIT" <<EOF
[Unit]
Description=ZEN one-shot OpenClaw persistence repair
After=user@0.service

[Service]
Type=oneshot
ExecStart=/bin/bash ${HELPER}
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=false
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true

EOF

cleanup() {
  rm -f "$SYSTEM_UNIT"
  systemctl daemon-reload >/dev/null 2>&1 || true
}
trap cleanup EXIT

rm -f "$STATUS"
systemctl daemon-reload
set +e
systemctl start zen-openclaw-persistence-repair.service
rc=$?
set -e

echo "=== persistence helper result ==="
if [[ -f "$STATUS" ]]; then
  cat "$STATUS"
else
  echo "PERSISTENCE_STATUS_FILE=MISSING"
fi

if [[ "$rc" -ne 0 ]]; then
  echo "=== helper service diagnostics ==="
  systemctl status zen-openclaw-persistence-repair.service --no-pager --lines=40 2>&1 || true
  exit "$rc"
fi

systemctl is-failed zen-openclaw-persistence-repair.service 2>/dev/null | grep -q failed && exit 32 || true

echo "ZEN_OPENCLAW_PERSISTENCE_HELPER=PASS"
