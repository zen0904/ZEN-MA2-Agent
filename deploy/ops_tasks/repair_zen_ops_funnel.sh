#!/usr/bin/env bash
set -euo pipefail

PORT=18991
TARGET="http://127.0.0.1:${PORT}"

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

echo "=== ensure funnel ==="
# Modern Tailscale accepts an HTTP URL target; --bg persists the serve/funnel
# configuration in tailscaled rather than depending on an interactive process.
if ! tailscale funnel --yes --bg "$TARGET"; then
  # Compatibility fallback for releases that expect a port target.
  tailscale funnel --yes --bg "$PORT"
fi

echo "=== final funnel status ==="
tailscale funnel status 2>&1 || true

echo "=== local result probe ==="
curl -fsS --max-time 5 "${TARGET}/latest.json" | head -c 4000
echo
