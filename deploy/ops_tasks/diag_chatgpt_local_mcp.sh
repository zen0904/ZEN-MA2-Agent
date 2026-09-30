#!/usr/bin/env bash
set -euo pipefail

echo "TASK=DIAG_CHATGPT_LOCAL_MCP"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

echo "=== CODEX MCP LIST ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   /usr/local/bin/codex mcp list 2>&1 || true

echo "=== CHATGPT PROCESS ==="
pgrep -a -u zenui -f '/usr/lib/chatgpt/ChatGPT|/usr/bin/chatgpt' || true

echo "=== CODEX CONFIG MCP BLOCKS ==="
python3 - <<'PY'
from pathlib import Path
p = Path("/var/lib/zenui/.codex/config.toml")
if not p.exists():
    print("NO_CONFIG")
else:
    lines = p.read_text(errors="replace").splitlines()
    emit = False
    for line in lines:
        if line.startswith("[mcp_servers.") or line.startswith("[mcp."):
            emit = True
            print(line)
            continue
        if emit and line.startswith("[") and not (line.startswith("[mcp_servers.") or line.startswith("[mcp.")):
            emit = False
        if emit:
            if any(k in line.lower() for k in ("token", "secret", "password", "key")):
                print("<redacted-sensitive-line>")
            else:
                print(line)
PY

echo "=== CHATGPT CONFIG CANDIDATES ==="
find /var/lib/zenui -maxdepth 5 -type f -printf '%p\n' 2>/dev/null   | grep -Ei 'chatgpt|codex|openai'   | grep -Ei 'config|settings|mcp|plugin'   | sort | head -200 || true

echo "=== APP RESOURCE MCP HINTS ==="
grep -RIl --binary-files=without-match -m 1   -E 'mcpServers|mcp_servers|MCP server|local MCP|plugin'   /usr/lib/chatgpt/resources 2>/dev/null | head -100 || true

echo "DIAG_CHATGPT_LOCAL_MCP=PASS"
