#!/usr/bin/env bash
set -euo pipefail

RESULT_PORT=18991
FUNNEL_HTTPS_PORT=10000
TARGET="http://127.0.0.1:${RESULT_PORT}"

check_active() {
  local unit="$1"
  systemctl is-active --quiet "$unit"
  echo "ACTIVE:${unit}=PASS"
}

check_enabled() {
  local unit="$1"
  systemctl is-enabled --quiet "$unit"
  echo "ENABLED:${unit}=PASS"
}

check_active zen-ops-worker.service
check_enabled zen-ops-worker.service
check_enabled zen-ops-updater.timer
check_active zen-ops-updater.timer
check_enabled zen-ops-results.service
check_active zen-ops-results.service

curl -fsS --max-time 5 "${TARGET}/" >/dev/null
echo "LOCAL_RESULTS_HTTP=PASS"

# Reassert the external result path exactly as the updater does.
systemctl start zen-ops-funnel.service
tailscale status >/dev/null
tailscale funnel status 2>&1 | sed -n '1,120p'
echo "FUNNEL_REASSERT=PASS"

if [[ -f /var/lib/zen-ops/public/latest.json ]]; then
  python3 - <<'PY'
import json
from pathlib import Path
p = Path('/var/lib/zen-ops/public/latest.json')
obj = json.loads(p.read_text())
print('LATEST_RESULT_JOB=' + str(obj.get('job_id', '')))
print('LATEST_RESULT_STATUS=' + str(obj.get('status', '')))
PY
else
  echo "LATEST_RESULT_FILE=ABSENT"
fi

echo "ZEN_OPS_RECOVERY_ACCEPTANCE=PASS"
echo "ZEN_OPS_RESULT_HTTPS_PORT=${FUNNEL_HTTPS_PORT}"
