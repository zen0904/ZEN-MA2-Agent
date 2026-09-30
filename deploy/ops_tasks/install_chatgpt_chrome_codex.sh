#!/usr/bin/env bash
set -euo pipefail

CHATGPT_URL="https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb"
CHROME_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
TMPDIR="$(mktemp -d /tmp/zen-ai-desktop-install.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

arch="$(uname -m)"
[[ "$arch" == "x86_64" ]] || { echo "UNSUPPORTED_ARCH=$arch"; exit 70; }
. /etc/os-release
[[ "$ID" == "ubuntu" && "$VERSION_ID" == "24.04" ]] || {
  echo "UNEXPECTED_OS=$ID $VERSION_ID"
  exit 71
}

avail_kb="$(df -Pk / | awk 'NR==2{print $4}')"
echo "ROOT_FREE_KB=$avail_kb"
if (( avail_kb < 2500000 )); then
  echo "INSUFFICIENT_DISK_FOR_CHATGPT_CHROME_CODEX"
  exit 72
fi

echo "=== download ChatGPT official Linux x64 package ==="
curl -fL --retry 3 --connect-timeout 20 -o "$TMPDIR/chatgpt_amd64.deb" "$CHATGPT_URL"
dpkg-deb -f "$TMPDIR/chatgpt_amd64.deb" Package Version Architecture | sed 's/^/CHATGPT_PKG=/'

echo "=== download Google Chrome stable ==="
curl -fL --retry 3 --connect-timeout 20 -o "$TMPDIR/google-chrome-stable_current_amd64.deb" "$CHROME_URL"
dpkg-deb -f "$TMPDIR/google-chrome-stable_current_amd64.deb" Package Version Architecture | sed 's/^/CHROME_PKG=/'

echo "=== install desktop packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y "$TMPDIR/chatgpt_amd64.deb" "$TMPDIR/google-chrome-stable_current_amd64.deb"

echo "=== install Codex CLI isolated ==="
NODE_HOME=/opt/node
NODE="$NODE_HOME/bin/node"
NPM_CLI="$NODE_HOME/lib/node_modules/npm/bin/npm-cli.js"
[[ -x "$NODE" && -f "$NPM_CLI" ]] || { echo "NODE_RUNTIME_INCOMPLETE"; exit 73; }
APP=/opt/zen/tools/codex-cli
STAGE=/opt/zen/tools/.codex-cli-install
rm -rf "$STAGE"
install -d -m 0755 /opt/zen/tools "$STAGE"
"$NODE" "$NPM_CLI" install --prefix "$STAGE" --no-audit --no-fund @openai/codex@latest
[[ -x "$STAGE/node_modules/.bin/codex" ]] || { echo "CODEX_BIN_MISSING"; exit 74; }
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

echo "=== verification ==="
command -v chatgpt
chatgpt --version 2>/dev/null || true
command -v google-chrome
google-chrome --version
command -v codex
codex --version
echo "DISPLAY_PRESENT=$([[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]] && echo YES || echo NO)"
echo "DEFAULT_TARGET=$(systemctl get-default 2>/dev/null || true)"
echo "CHATGPT_INSTALL=PASS"
echo "CHROME_INSTALL=PASS"
echo "CODEX_INSTALL=PASS"
