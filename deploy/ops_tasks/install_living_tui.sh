#!/usr/bin/env bash
set -euo pipefail

R=/opt/zen/zen-ops-runtime
echo "TASK=INSTALL_LIVING_TUI"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

python3 -c 'from pathlib import Path; p=Path("'"$R"'/deploy/ubuntu/zen-living-tui.py"); compile(p.read_text(encoding="utf-8"), str(p), "exec")'
bash -n "$R/deploy/ubuntu/zen-control-room-layout"
bash -n "$R/deploy/ubuntu/zen-chatgpt-session.sh"

if ! command -v xterm >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y --no-install-recommends xterm
fi

install -m 0755 "$R/deploy/ubuntu/zen-living-tui.py" /usr/local/bin/zen-living-tui

systemctl disable --now zen-living-visualizer.service >/dev/null 2>&1 || true

echo "XTERM=$(command -v xterm)"
echo "TUI=/usr/local/bin/zen-living-tui"
echo "WEB_VISUALIZER=$(systemctl is-active zen-living-visualizer.service 2>/dev/null || true)"
echo "RESULT=PASS"
