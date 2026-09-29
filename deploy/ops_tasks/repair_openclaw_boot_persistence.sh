#!/usr/bin/env bash
set -euo pipefail

# Compatibility alias retained for old ops jobs. OpenClaw on the Mini is a
# root systemd --user service, not a system-level service. Keep one authority
# path so an old repair job cannot create a second gateway competing for 18789.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec /bin/bash "${SCRIPT_DIR}/repair_openclaw_gateway_boot.sh" "$@"
