#!/usr/bin/env bash
set -euo pipefail

NPM=/opt/node/bin/npm
CODEX=/opt/node/bin/codex

if [[ ! -x "$NPM" ]]; then
  echo "NPM_MISSING=$NPM" >&2
  exit 2
fi

export PATH=/opt/node/bin:/usr/local/bin:/usr/bin:/bin
export HOME=/var/lib/zen-ops

"$NPM" install -g @openai/codex

echo "=== CODEX ==="
"$CODEX" --version

echo "=== SAFETY ==="
echo "CHATGPT_LOGIN_PERFORMED=0"
echo "OPENAI_API_KEY_WRITTEN=0"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
