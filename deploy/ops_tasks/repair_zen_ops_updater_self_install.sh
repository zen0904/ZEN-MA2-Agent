#!/usr/bin/env bash
set -euo pipefail

R=/opt/zen/zen-ops-runtime
LIVE=/usr/local/sbin/zen-ops-update

echo "REPAIR=ZEN_OPS_UPDATER_SELF_INSTALL"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -f "$R/deploy/ubuntu/zen-ops-update"
install -m 0755 "$R/deploy/ubuntu/zen-ops-update" "$LIVE"

echo "LIVE_UPDATER_SHA256=$(sha256sum "$LIVE" | awk '{print $1}')"
echo "RUNTIME_HEAD=$(git -C "$R" rev-parse --short HEAD)"

GH_CONFIG_DIR=/var/lib/zen-ops/gh "$LIVE"

test -f /var/lib/zen-ops/public/updater-heartbeat.json
echo "HEARTBEAT=PASS"
cat /var/lib/zen-ops/public/updater-heartbeat.json
echo "REPAIR_COMPLETE=PASS"
