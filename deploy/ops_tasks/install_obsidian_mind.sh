#!/usr/bin/env bash
set -euo pipefail

VAULT=/var/lib/zenui/obsidian-mind
REPO=https://github.com/breferrari/obsidian-mind.git
CODEX=/usr/local/bin/codex
NODE="$(command -v node)"

echo "TASK=INSTALL_OBSIDIAN_MIND"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

id zenui >/dev/null
test -x "$CODEX"
test -n "$NODE"
test -x "$NODE"

if [[ -d "$VAULT/.git" ]]; then
  git -C "$VAULT" fetch --depth=1 origin main
  git -C "$VAULT" reset --hard origin/main
else
  rm -rf "$VAULT"
  git clone --depth=1 "$REPO" "$VAULT"
fi

chown -R zenui:zenui "$VAULT"

echo "VAULT_HEAD=$(git -C "$VAULT" rev-parse --short HEAD)"
echo "VAULT_VERSION=$(python3 - <<'PY'
import json
from pathlib import Path
p=Path("/var/lib/zenui/obsidian-mind/vault-manifest.json")
print(json.loads(p.read_text()).get("version","unknown"))
PY
)"

cat >"$VAULT/brain/ZEN Agent Server.md" <<'EOF'
---
date: 2026-09-30
description: "Integration boundary for the ZEN Agent Server and Obsidian Mind memory layer."
tags:
  - brain
  - zen
  - agent-server
---

# ZEN Agent Server

This vault is an advisory persistent-memory layer for local coding agents.

## Authority boundary

- The committed ZEN repository remains the canonical source of truth.
- AGENTS.md, data/zen_project_control.json, ZEN contracts, tests, native MA2 evidence, Preview/Approval, and deterministic Builder/readback override vault memories.
- A memory may help recall context, decisions, gotchas, and prior reasoning, but it must never silently authorize an MA2/MA3 write or override current repository state.
- MA2/MA3 writes remain separately gated.
EOF
chown zenui:zenui "$VAULT/brain/ZEN Agent Server.md"

runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin "$CODEX" mcp remove om >/dev/null 2>&1 || true
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin "$CODEX" mcp add om -- "$NODE" "$VAULT/.claude/scripts/om-mcp.mjs"

echo "=== MCP LIST ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin "$CODEX" mcp list

echo "=== MCP GET OM ==="
runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin "$CODEX" mcp get om

echo "=== OM SERVER SMOKE ==="
rc=0
timeout 8s runuser -u zenui -- env HOME=/var/lib/zenui PATH=/usr/local/bin:/usr/bin:/bin "$NODE" "$VAULT/.claude/scripts/om-mcp.mjs" </dev/null >/tmp/zen-om-mcp.out 2>/tmp/zen-om-mcp.err || rc=$?
echo "OM_SMOKE_RC=$rc"
head -40 /tmp/zen-om-mcp.err 2>/dev/null || true

echo "QMD_INSTALLED=$(command -v qmd >/dev/null 2>&1 && echo YES || echo NO)"
echo "OBSIDIAN_MIND=PASS"
