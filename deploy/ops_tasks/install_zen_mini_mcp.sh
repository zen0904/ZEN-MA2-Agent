#!/usr/bin/env bash
set -euo pipefail

SRC=/opt/zen/zen-ops-runtime/deploy/ubuntu/zen-mini-mcp
DST=/opt/zen/zen-mini-mcp
NODE="$(command -v node)"
NPM="$(command -v npm)"
CODEX=/usr/local/bin/codex

echo "TASK=INSTALL_ZEN_MINI_LOCAL_MCP"
echo "TRANSPORT=stdio"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -d "$SRC"
test -n "$NODE"
test -x "$NODE"
test -n "$NPM"
test -x "$NPM"
test -x "$CODEX"
id zenui >/dev/null

# Remove the abandoned HTTP-service experiment if it exists.
systemctl disable --now zen-mini-mcp.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/zen-mini-mcp.service
systemctl daemon-reload

install -d -m 0755 "$DST"
install -m 0644 "$SRC/package.json" "$DST/package.json"
install -m 0644 "$SRC/server.mjs" "$DST/server.mjs"
install -m 0644 "$SRC/smoke.mjs" "$DST/smoke.mjs"

install -d -m 0755 /var/cache/zen-mini-mcp-npm
cd "$DST"
NPM_CONFIG_CACHE=/var/cache/zen-mini-mcp-npm "$NPM" install --omit=dev --no-audit --no-fund
chown -R root:root "$DST"
chmod -R a+rX "$DST"

# Register globally for the same zenui identity used by the Mini ChatGPT/Codex app.
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   "$CODEX" mcp remove zen-mini >/dev/null 2>&1 || true

runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   "$CODEX" mcp add zen-mini -- "$NODE" "$DST/server.mjs"

echo "=== MCP GET ZEN-MINI ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   "$CODEX" mcp get zen-mini

echo "=== MCP LIST FILTER ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   "$CODEX" mcp list | grep -E '(^Name|zen-mini|om[[:space:]])' || true

echo "=== OFFICIAL CLIENT SMOKE ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   "$NODE" "$DST/smoke.mjs"

# Force the desktop app to reload its MCP config. Login state lives under zenui HOME.
systemctl restart zen-chatgpt-desktop.service
sleep 5

echo "CHATGPT_DESKTOP_ACTIVE=$(systemctl is-active zen-chatgpt-desktop.service || true)"
echo "CHATGPT_PID=$(pgrep -u zenui -f '/usr/lib/chatgpt/ChatGPT' | head -1 || true)"
echo "ZEN_MINI_LOCAL_MCP=PASS"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
