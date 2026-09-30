#!/usr/bin/env bash
set -euo pipefail
echo "TASK=INSPECT_CODEX_EXEC_HELP"
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin   /usr/local/bin/codex exec --help 2>&1 | sed -n '1,220p'
echo "INSPECT_CODEX_EXEC_HELP=PASS"
