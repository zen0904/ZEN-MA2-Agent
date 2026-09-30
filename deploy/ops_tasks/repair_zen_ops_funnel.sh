#!/usr/bin/env bash
set -euo pipefail

PORT=18991
HTTPS_PORT=10000
TARGET="http://127.0.0.1:${PORT}"
RUNTIME_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== install bounded recovery units ==="
install -m 0644 "${RUNTIME_ROOT}/deploy/ubuntu/systemd/zen-ops-results.service" /etc/systemd/system/zen-ops-results.service
install -m 0644 "${RUNTIME_ROOT}/deploy/ubuntu/systemd/zen-ops-funnel.service" /etc/systemd/system/zen-ops-funnel.service
systemctl daemon-reload
systemctl enable zen-ops-results.service zen-ops-funnel.service >/dev/null

echo "=== zen ops result service ==="
systemctl enable --now zen-ops-results.service
systemctl is-active zen-ops-results.service
ss -ltn | grep -E "127\\.0\\.0\\.1:${PORT}[[:space:]]" || {
  echo "result server is not listening on ${PORT}" >&2
  exit 21
}

echo "=== tailscale ==="
systemctl enable --now tailscaled.service
systemctl is-active tailscaled.service
tailscale status >/dev/null

echo "=== current funnel status ==="
tailscale funnel status 2>&1 || true

echo "=== ensure dedicated ZEN Ops funnel ==="
# Keep ZEN Ops result retrieval on its dedicated HTTPS listener. Port 443 is
# reserved for the OpenClaw-facing managed Serve/Funnel surface and must not be
# claimed by this repair task.
tailscale funnel --yes --bg --https="${HTTPS_PORT}" "${TARGET}"

echo "=== final funnel status ==="
tailscale funnel status 2>&1 || true

echo "=== local result probe ==="
curl -fsS --max-time 5 "${TARGET}/latest.json" | head -c 4000
echo

echo "ZEN_OPS_RESULT_HTTPS_PORT=${HTTPS_PORT}"
