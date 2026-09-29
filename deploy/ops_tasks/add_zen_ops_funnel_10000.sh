#!/usr/bin/env bash
set -euo pipefail

echo "=== before ==="
tailscale funnel status --json || true

echo "=== add ZEN Ops result funnel on 10000 ==="
tailscale funnel --yes --bg --https=10000 http://127.0.0.1:18991

echo "=== after ==="
tailscale funnel status --json

echo "ZEN_OPS_RESULT_URL=https://zen-agent-server.tail3e0394.ts.net:10000/latest.json"
