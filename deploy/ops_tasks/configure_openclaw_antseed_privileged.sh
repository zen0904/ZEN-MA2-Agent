#!/usr/bin/env bash
set -euo pipefail

RUNTIME=/opt/zen/zen-ops-runtime
HELPER=${RUNTIME}/deploy/ops_tasks/configure_openclaw_antseed_helper.sh
SYSTEM_UNIT=/etc/systemd/system/zen-openclaw-antseed-config.service
STATUS=/var/lib/zen-ops/openclaw-antseed-config-status.txt

[[ -f "$HELPER" ]] || { echo OPENCLAW_ANTSEED_HELPER=MISSING; exit 31; }

cat >"$SYSTEM_UNIT" <<EOF
[Unit]
Description=ZEN one-shot OpenClaw Antseed provider configuration
After=user@0.service zen-antseed-buyer.service
Wants=zen-antseed-buyer.service

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
systemctl start zen-openclaw-antseed-config.service
rc=$?
set -e

echo '=== privileged helper result ==='
if [[ -f "$STATUS" ]]; then
  cat "$STATUS"
else
  echo OPENCLAW_ANTSEED_STATUS_FILE=MISSING
fi

if [[ "$rc" -ne 0 ]]; then
  echo '=== helper service diagnostics ==='
  systemctl status zen-openclaw-antseed-config.service --no-pager --lines=40 2>&1 || true
  exit "$rc"
fi

echo ZEN_OPENCLAW_ANTSEED_PRIVILEGED=PASS
