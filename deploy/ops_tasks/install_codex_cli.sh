#!/usr/bin/env bash
set -euo pipefail

NODE_HOME=/opt/node
NODE="$NODE_HOME/bin/node"
NPM_CLI="$NODE_HOME/lib/node_modules/npm/bin/npm-cli.js"
APP=/opt/zen/tools/codex-cli
STAGE=/opt/zen/tools/.codex-cli-install
BUILD_HOME=/var/lib/zen-ops/codex-build-home
NPM_CACHE=/var/lib/zen-ops/codex-npm-cache

[[ -x "$NODE" && -f "$NPM_CLI" ]] || { echo "NODE_RUNTIME_INCOMPLETE"; exit 70; }
install -d -m 0755 /opt/zen/tools
install -d -o zenops -g zenops -m 0700 "$BUILD_HOME" "$NPM_CACHE"
rm -rf "$STAGE"
install -d -m 0755 "$STAGE"

export HOME="$BUILD_HOME"
export npm_config_cache="$NPM_CACHE"
export PATH="$NODE_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

"$NODE" "$NPM_CLI" install --prefix "$STAGE" --no-audit --no-fund @openai/codex@latest
[[ -x "$STAGE/node_modules/.bin/codex" ]] || { echo "CODEX_BIN_MISSING"; exit 71; }

rm -rf "$APP"
mv "$STAGE" "$APP"
chown -R root:root "$APP"

cat >/usr/local/bin/codex <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
exec /opt/zen/tools/codex-cli/node_modules/.bin/codex "$@"
EOF
chmod 0755 /usr/local/bin/codex

command -v codex
codex --version
echo "CODEX_INSTALL=PASS"
