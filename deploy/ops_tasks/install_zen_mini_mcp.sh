#!/usr/bin/env bash
set -euo pipefail

SRC=/opt/zen/zen-ops-runtime/deploy/ubuntu/zen-mini-mcp
DST=/opt/zen/zen-mini-mcp
SERVICE=/etc/systemd/system/zen-mini-mcp.service
NODE="$(command -v node)"
NPM="$(command -v npm)"

echo "TASK=INSTALL_ZEN_MINI_MCP"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -d "$SRC"
test -n "$NODE"
test -x "$NODE"
test -n "$NPM"
test -x "$NPM"
id zenui >/dev/null

install -d -m 0755 "$DST"
install -m 0644 "$SRC/package.json" "$DST/package.json"
install -m 0644 "$SRC/server.mjs" "$DST/server.mjs"
install -m 0644 "$SRC/smoke.mjs" "$DST/smoke.mjs"

install -d -m 0755 /var/cache/zen-mini-mcp-npm
cd "$DST"
NPM_CONFIG_CACHE=/var/cache/zen-mini-mcp-npm "$NPM" install --omit=dev --no-audit --no-fund
chown -R root:root "$DST"
chmod -R a+rX "$DST"

cat >"$SERVICE" <<EOF
[Unit]
Description=ZEN Mini bounded read-only MCP gateway
After=network.target zen-ops-results.service
Wants=zen-ops-results.service

[Service]
Type=simple
User=zenui
Group=zenui
WorkingDirectory=$DST
Environment=HOME=/var/lib/zenui
Environment=ZEN_MINI_MCP_PORT=19090
ExecStart=$NODE $DST/server.mjs
Restart=on-failure
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=full
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=false

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now zen-mini-mcp.service

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:19090/healthz >/tmp/zen-mini-mcp-health.json 2>/dev/null; then
    break
  fi
  sleep 1
done

cat /tmp/zen-mini-mcp-health.json
systemctl --no-pager --full status zen-mini-mcp.service | sed -n '1,30p'

cd "$DST"
"$NODE" "$DST/smoke.mjs"

echo "ZEN_MINI_MCP_INSTALL=PASS"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
