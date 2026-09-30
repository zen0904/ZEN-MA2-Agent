#!/usr/bin/env bash
set -euo pipefail

R=/opt/zen/zen-ops-runtime
APP=/usr/local/bin/zen-living-visualizer
UNIT=/etc/systemd/system/zen-living-visualizer.service

echo "TASK=INSTALL_LIVING_VISUALIZER"
echo "AUTHORITY=OBSERVATION_ONLY"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -f "$R/deploy/ubuntu/zen-living-visualizer.py"
test -f "$R/deploy/ubuntu/systemd/zen-living-visualizer.service"

install -m 0755 "$R/deploy/ubuntu/zen-living-visualizer.py" "$APP"
install -m 0644 "$R/deploy/ubuntu/systemd/zen-living-visualizer.service" "$UNIT"

systemctl daemon-reload
systemctl enable zen-living-visualizer.service >/dev/null
systemctl restart zen-living-visualizer.service
sleep 1

echo "SERVICE=$(systemctl is-active zen-living-visualizer.service)"
echo "HEALTH=$(curl -fsS --max-time 4 http://127.0.0.1:18992/health)"
echo "STATE=$(curl -fsS --max-time 4 http://127.0.0.1:18992/api/state | head -c 2000)"
echo
echo "VISUALIZER_URL=http://127.0.0.1:18992/"
echo "RESULT=PASS"
