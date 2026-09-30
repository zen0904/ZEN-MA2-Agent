#!/usr/bin/env bash
set -euo pipefail

SRC_ROOT=/opt/node-v22-backup-20260928-213623
SRC="$SRC_ROOT/lib/node_modules/@wonderwhy-er/desktop-commander"
DST_ROOT=/opt/node/lib/node_modules/@wonderwhy-er
DST="$DST_ROOT/desktop-commander"
UNIT=desktop-commander-remote.service

echo "REPAIR=DESKTOP_COMMANDER_REMOTE"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

test -x /opt/node/bin/node
test -f "$SRC/dist/index.js"
test -f "$SRC/package.json"

install -d -m 0755 "$DST_ROOT"
rm -rf "$DST_ROOT/desktop-commander.restore-tmp"
cp -a "$SRC" "$DST_ROOT/desktop-commander.restore-tmp"
rm -rf "$DST"
mv "$DST_ROOT/desktop-commander.restore-tmp" "$DST"
ln -sfn ../lib/node_modules/@wonderwhy-er/desktop-commander/dist/index.js /opt/node/bin/desktop-commander

systemctl reset-failed "$UNIT" || true
systemctl restart "$UNIT"
sleep 3

echo "ACTIVE_STATE=$(systemctl is-active "$UNIT" 2>/dev/null || true)"
echo "SUB_STATE=$(systemctl show "$UNIT" -p SubState --value 2>/dev/null || true)"
echo "N_RESTARTS=$(systemctl show "$UNIT" -p NRestarts --value 2>/dev/null || true)"
echo "VERSION=$(/opt/node/bin/node -p "require('/opt/node/lib/node_modules/@wonderwhy-er/desktop-commander/package.json').version")"

if [[ "$(systemctl is-active "$UNIT" 2>/dev/null || true)" != "active" ]]; then
  echo "RESULT=FAIL"
  exit 41
fi

echo "RESULT=PASS"
