#!/usr/bin/env bash
set -euo pipefail

SRC=/opt/zen/tools/openchatx-linux-sandbox
STATE=/var/lib/zen-openchatx
NODE=/opt/node/bin/node
NPM=/opt/node/bin/npm
UPSTREAM=https://github.com/XiaoPuOuO/openchatx-mcp.git

id zenopenchatx >/dev/null 2>&1 || useradd --system --create-home --home-dir "$STATE" --shell /usr/sbin/nologin zenopenchatx
install -d -o root -g root -m 0755 /opt/zen/tools
install -d -o zenopenchatx -g zenopenchatx -m 0750 "$STATE" "$STATE/state" "$STATE/workspaces" "$STATE/npm-cache"

if [[ -d "$SRC/.git" ]]; then
  git -C "$SRC" fetch -q --depth 1 origin main
  git -C "$SRC" reset -q --hard origin/main
else
  rm -rf "$SRC"
  git clone -q --depth 1 "$UPSTREAM" "$SRC"
fi

cd "$SRC"
# npm/node-gyp inherits root HOME when repo_task runs as root. Keep every build
# cache inside the dedicated OpenChatX state tree instead of touching /root.
install -d -o zenopenchatx -g zenopenchatx -m 0750 "$STATE/home" "$STATE/node-gyp-cache"
export HOME="$STATE/home"
export XDG_CACHE_HOME="$STATE/home/.cache"
export npm_config_cache="$STATE/npm-cache"
export npm_config_devdir="$STATE/node-gyp-cache"
export npm_config_force=true
install -d -o zenopenchatx -g zenopenchatx -m 0750 "$XDG_CACHE_HOME"
"$NPM" ci
"$NPM" run build

cat >"$STATE/config.toml" <<'EOF'
state_dir = "/var/lib/zen-openchatx/state"
port = 18001

[shell]
path = "/bin/bash"
rtk = false

[tunnel]
profile = "openchatx"
health_port = 18080

[context]
warning_threshold = 400000

[mcp]
tool_output = "compact"

[tools]
shell = true
apply_patch = false
file_read = true
file_write = true
web = true
skills = true
image = true
EOF

chown -R zenopenchatx:zenopenchatx "$STATE"
chmod 0600 "$STATE/config.toml"

cat >/etc/systemd/system/zen-openchatx.service <<'EOF'
[Unit]
Description=ZEN OpenChatX Linux compatibility sandbox
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=zenopenchatx
Group=zenopenchatx
WorkingDirectory=/opt/zen/tools/openchatx-linux-sandbox
Environment=OPENCHATX_PUBLIC_CONFIG=/var/lib/zen-openchatx/config.toml
Environment=HOME=/var/lib/zen-openchatx
Environment=PATH=/opt/node/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/node/bin/node /opt/zen/tools/openchatx-linux-sandbox/dist/index.js
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=/var/lib/zen-openchatx

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now zen-openchatx.service >/dev/null
sleep 5

systemctl is-active zen-openchatx.service
curl -fsS -o /dev/null http://127.0.0.1:18001/ui || true
printf 'HEAD='
git -C "$SRC" rev-parse --short HEAD
printf 'PORT='
ss -ltn | grep -q ':18001 ' && echo LISTEN || echo DOWN
