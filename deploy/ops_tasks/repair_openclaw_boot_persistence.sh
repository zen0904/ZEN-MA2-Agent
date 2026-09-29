#!/usr/bin/env bash
set -euo pipefail

OPENCLAW=/opt/node/bin/openclaw
UNIT=/etc/systemd/system/zen-openclaw-gateway.service
PORT=18789

[[ -x "$OPENCLAW" ]] || { echo "openclaw binary missing" >&2; exit 31; }

# Discover existing state without printing credential-bearing config contents.
declare -a candidates=()
while IFS= read -r cfg; do
  [[ -f "$cfg" ]] || continue
  if python3 - "$cfg" "$PORT" <<\'PY\'
import json, sys
p=sys.argv[1]; port=int(sys.argv[2])
try:
    d=json.load(open(p, encoding="utf-8"))
except Exception:
    raise SystemExit(1)
g=d.get("gateway") if isinstance(d,dict) else None
plugins=d.get("plugins") if isinstance(d,dict) else None
port_ok=isinstance(g,dict) and int(g.get("port", port) or port)==port
plugin_text=json.dumps(plugins, ensure_ascii=False) if plugins is not None else ""
zen_hint="zen-ma2" in plugin_text.lower() or "zen_ma2" in plugin_text.lower()
raise SystemExit(0 if (port_ok or zen_hint) else 1)
PY
  then
    candidates+=("$cfg")
  fi
done < <(
  find /root /home /var/lib /opt/zen -maxdepth 5 \
    \( -path "*/node_modules" -o -path "*/.git" -o -path "*/npm-cache" \) -prune -o \
    -type f -name "openclaw.json" -print 2>/dev/null
)

if [[ "${#candidates[@]}" -ne 1 ]]; then
  echo "refusing: expected exactly one existing OpenClaw config candidate; found ${#candidates[@]}" >&2
  exit 32
fi

CONFIG="${candidates[0]}"
STATE_DIR="$(dirname "$CONFIG")"
OWNER="$(stat -c %U "$CONFIG")"
GROUP="$(stat -c %G "$CONFIG")"
OWNER_HOME="$(getent passwd "$OWNER" | cut -d: -f6)"
[[ -n "$OWNER_HOME" && -d "$OWNER_HOME" ]] || OWNER_HOME="$(dirname "$STATE_DIR")"

echo "CONFIG_SELECTED=YES"
echo "STATE_OWNER=${OWNER}:${GROUP}"
echo "PORT=${PORT}"

cat >"$UNIT" <<EOF
[Unit]
Description=ZEN managed OpenClaw Gateway
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=${OWNER}
Group=${GROUP}
Environment=HOME=${OWNER_HOME}
Environment=OPENCLAW_STATE_DIR=${STATE_DIR}
Environment=OPENCLAW_CONFIG_PATH=${CONFIG}
Environment=PATH=/opt/node/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/node/bin/openclaw gateway --bind loopback --port ${PORT}
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now zen-openclaw-gateway.service
sleep 4
systemctl is-active zen-openclaw-gateway.service
systemctl is-enabled zen-openclaw-gateway.service

if ! ss -ltn | grep -qE "127\\.0\\.0\\.1:${PORT}[[:space:]]"; then
  echo "gateway service active but port ${PORT} is not listening" >&2
  journalctl -u zen-openclaw-gateway.service -n 80 --no-pager 2>&1 | sed -E "s/(token|password|secret)([=: ][^ ]+)/\\1=[REDACTED]/Ig" | head -120
  exit 33
fi

echo "OPENCLAW_GATEWAY=ACTIVE"
echo "OPENCLAW_PORT=LISTEN"
"$OPENCLAW" --version
