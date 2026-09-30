#!/usr/bin/env bash
set -euo pipefail

CODEX=/usr/local/bin/codex
[[ -x "$CODEX" ]] || { echo "CODEX_MISSING"; exit 70; }
command -v openvt >/dev/null 2>&1 || { echo "OPENVT_MISSING"; exit 71; }

# Do not expose the one-time device code through ZEN Ops logs.
# Launch the device-auth flow directly on VT2 and switch the physical console to it.
pkill -f "codex login --device-auth" >/dev/null 2>&1 || true

cat >/tmp/zen-codex-vt2.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export HOME=/root
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
clear
echo "Codex device login"
echo
echo "Use your phone to open the URL / scan the QR shown here, then approve the login."
echo "This one-time code is shown only on the Mini console."
echo
exec /usr/local/bin/codex login --device-auth
EOF
chmod 0700 /tmp/zen-codex-vt2.sh

# -f force-open VT2, -s switch console to it.
# Run detached so the ops task can return without killing the interactive login.
setsid openvt -f -c 2 -s -- /tmp/zen-codex-vt2.sh >/dev/null 2>&1 < /dev/null &

sleep 2
echo "CODEX_DEVICE_AUTH_VT=2"
echo "CONSOLE_SWITCH_REQUESTED=YES"
echo "DEVICE_CODE_EXPOSED_TO_OPS=NO"
