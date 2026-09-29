#!/usr/bin/env bash
set -euo pipefail

APP=/opt/zen/tools/antseed-cli
STAGE=/opt/zen/tools/.antseed-cli-install
STATE=/var/lib/zen-antseed
SERVICE_USER=zenantseed
VERSION="${ANTSEED_VERSION:-0.1.165}"

pick_node_home() {
  local candidate
  shopt -s nullglob
  for candidate in /opt/node-v22*/bin/node; do
    if [[ -x "$candidate" ]]; then
      dirname "$(dirname "$candidate")"
      return 0
    fi
  done
  if [[ -x /opt/node/bin/node ]]; then
    echo /opt/node
    return 0
  fi
  return 1
}

NODE_HOME="$(pick_node_home)" || {
  echo "No supported Node runtime found under /opt/node*" >&2
  exit 70
}
NODE="$NODE_HOME/bin/node"
NPM_CLI="$NODE_HOME/lib/node_modules/npm/bin/npm-cli.js"
[[ -x "$NODE" && -f "$NPM_CLI" ]] || {
  echo "Node/npm runtime is incomplete: $NODE_HOME" >&2
  exit 70
}

major="$("$NODE" -p 'Number(process.versions.node.split(".")[0])')"
if (( major < 20 )); then
  echo "Antseed requires Node 20+; found $("$NODE" -v)" >&2
  exit 70
fi

id "$SERVICE_USER" >/dev/null 2>&1 ||   useradd --system --create-home --home-dir "$STATE" --shell /usr/sbin/nologin "$SERVICE_USER"

install -d -o root -g root -m 0755 /opt/zen/tools
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0700 "$STATE" "$STATE/runtime"
install -d -o root -g root -m 0755 "$STATE/build-home" "$STATE/npm-cache" "$STATE/node-gyp-cache"

systemctl stop zen-antseed-buyer.service >/dev/null 2>&1 || true
rm -rf "$STAGE"
install -d -o root -g root -m 0755 "$STAGE"

export HOME="$STATE/build-home"
export XDG_CACHE_HOME="$STATE/build-home/.cache"
export npm_config_cache="$STATE/npm-cache"
export npm_config_devdir="$STATE/node-gyp-cache"
export PATH="$NODE_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
install -d -o root -g root -m 0755 "$XDG_CACHE_HOME"

"$NODE" "$NPM_CLI" install   --prefix "$STAGE"   --no-audit   --no-fund   "@antseed/cli@$VERSION"

CLI="$STAGE/node_modules/@antseed/cli/dist/cli/index.js"
[[ -f "$CLI" ]] || {
  echo "Antseed CLI entrypoint missing after install" >&2
  exit 71
}
"$NODE" "$CLI" --version

rm -rf "$APP"
mv "$STAGE" "$APP"
chown -R root:root "$APP"

cat >/usr/local/bin/zen-antseed <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PATH="$NODE_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
exec "$NODE" "$APP/node_modules/@antseed/cli/dist/cli/index.js" "\$@"
EOF
chmod 0755 /usr/local/bin/zen-antseed

install -m 0644   /opt/zen/zen-ops-runtime/deploy/ubuntu/systemd/zen-antseed-buyer.service   /etc/systemd/system/zen-antseed-buyer.service

systemctl daemon-reload
systemctl enable --now zen-antseed-buyer.service >/dev/null

for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 http://127.0.0.1:8377/v1/models >/tmp/zen-antseed-models.json 2>/dev/null; then
    break
  fi
  sleep 2
done

systemctl is-active zen-antseed-buyer.service
ss -ltn | grep -q '127.0.0.1:8377 ' || {
  echo "Antseed buyer is not listening on loopback:8377" >&2
  journalctl -u zen-antseed-buyer.service -n 80 --no-pager
  exit 72
}

python3 - <<'PY'
import json
from pathlib import Path

path = Path("/tmp/zen-antseed-models.json")
if not path.exists():
    raise SystemExit("models response was not captured")
payload = json.loads(path.read_text())
items = payload.get("data", []) if isinstance(payload, dict) else []
ids = [str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")]
print("MODELS_COUNT=" + str(len(ids)))
print("MODELS_SAMPLE=" + ",".join(ids[:20]))
print("DEEPSEEK_V4_FLASH=" + ("YES" if "deepseek-v4-flash" in ids else "NO"))
print("GLM_5_3_FLASH=" + ("YES" if "glm-5.3-flash" in ids else "NO"))
PY

rm -f /tmp/zen-antseed-models.json
echo "ANTSEED_BIND=127.0.0.1:8377"
echo "ANTSEED_PAYMENT_MODE=DISABLED"
echo "ANTSEED_MAX_INPUT_USD_PER_MILLION=0"
echo "ANTSEED_MAX_OUTPUT_USD_PER_MILLION=0"
