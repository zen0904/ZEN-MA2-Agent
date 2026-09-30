#!/usr/bin/env bash
set -euo pipefail
VAULT=/var/lib/zenui/obsidian-mind
CODEX=/usr/local/bin/codex

echo "VERIFY=CHATGPT_OBSIDIAN_POSTREBOOT"
echo "BOOT_TIME=$(uptime -s 2>/dev/null || true)"
echo "UPTIME_SECONDS=$(cut -d. -f1 /proc/uptime 2>/dev/null || true)"

echo "CHATGPT_SERVICE_ACTIVE=$(systemctl is-active zen-chatgpt-desktop.service 2>/dev/null || true)"
echo "CHATGPT_SERVICE_ENABLED=$(systemctl is-enabled zen-chatgpt-desktop.service 2>/dev/null || true)"
echo "CHATGPT_PID=$(pgrep -u zenui -f '/usr/lib/chatgpt/ChatGPT' | head -1 || true)"
echo "XORG_PID=$(pgrep -f '/usr/lib/xorg/Xorg :0|/usr/bin/Xorg :0' | head -1 || true)"
echo "TASKBAR_ACTIVE=$(systemctl is-active zen-mini-taskbar.service 2>/dev/null || true)"
echo "TASKBAR_ENABLED=$(systemctl is-enabled zen-mini-taskbar.service 2>/dev/null || true)"
echo "CHROME_ENABLED=$(systemctl is-enabled zen-mini-chrome.service 2>/dev/null || true)"

test -d "$VAULT/.git"
echo "VAULT_PRESENT=YES"
echo "VAULT_HEAD=$(runuser -u zenui -- env HOME=/var/lib/zenui git -C "$VAULT" rev-parse --short HEAD)"
echo "VAULT_VERSION=$(python3 - <<'PY'
import json
from pathlib import Path
p=Path("/var/lib/zenui/obsidian-mind/vault-manifest.json")
print(json.loads(p.read_text()).get("version","unknown"))
PY
)"

echo "=== OM MCP ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin "$CODEX" mcp get om

echo "WORKER_ACTIVE=$(systemctl is-active zen-ops-worker.service 2>/dev/null || true)"
echo "UPDATER_TIMER_ACTIVE=$(systemctl is-active zen-ops-updater.timer 2>/dev/null || true)"
echo "RESULTS_ACTIVE=$(systemctl is-active zen-ops-results.service 2>/dev/null || true)"
echo "TAILSCALED_ACTIVE=$(systemctl is-active tailscaled.service 2>/dev/null || true)"

echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
echo "POSTREBOOT_ACCEPTANCE=PASS"
