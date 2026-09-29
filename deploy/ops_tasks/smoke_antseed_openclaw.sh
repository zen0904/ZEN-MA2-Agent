#!/usr/bin/env bash
set -euo pipefail

OPENCLAW=/opt/node/bin/openclaw

if [[ "${ZEN_ANTSEED_SMOKE_CHILD:-0}" != "1" ]]; then
  unit="zen-antseed-openclaw-smoke-$(date +%s)"
  exec systemd-run --quiet --wait --collect --pipe \
    --unit="$unit" \
    --setenv=ZEN_ANTSEED_SMOKE_CHILD=1 \
    /bin/bash "$0"
fi

export HOME=/root
export OPENCLAW_STATE_DIR=/root/.openclaw
export OPENCLAW_CONFIG_PATH=/root/.openclaw/openclaw.json

out="$(mktemp)"
err="$(mktemp)"
session="antseed-smoke-$(date +%Y%m%d%H%M%S)"
cleanup() { rm -f "$out" "$err"; }
trap cleanup EXIT

if ! "$OPENCLAW" agent \
  --agent main \
  --session-key "$session" \
  --model antseed/deepseek-v4-flash \
  --thinking off \
  --timeout 180 \
  --message "Do not call tools. Reply with exact ASCII text OK only." \
  --json >"$out" 2>"$err"; then
  echo "OPENCLAW_AGENT_SMOKE=FAIL"
  sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' "$err" | tail -80
  exit 1
fi

python3 - "$out" <<'PY'
import json, sys
p=json.load(open(sys.argv[1]))
payloads=p.get("payloads") if isinstance(p,dict) else None
reply=""
if isinstance(payloads,list):
    for item in payloads:
        if isinstance(item,dict) and isinstance(item.get("text"),str):
            reply=item["text"].strip()
            if reply:
                break
if not reply and isinstance(p,dict) and isinstance(p.get("final"),str):
    reply=p["final"].strip()
meta=p.get("meta",{}) if isinstance(p,dict) else {}
agent_meta=meta.get("agentMeta",{}) if isinstance(meta,dict) else {}
provider=(p.get("provider") if isinstance(p,dict) else None) or (agent_meta.get("provider") if isinstance(agent_meta,dict) else None)
model=(p.get("model") if isinstance(p,dict) else None) or (agent_meta.get("model") if isinstance(agent_meta,dict) else None)
status=(p.get("status") if isinstance(p,dict) else None) or ("ok" if reply else "unknown")
print("OPENCLAW_AGENT_SMOKE=PASS")
print("STATUS="+str(status))
print("PROVIDER="+str(provider))
print("MODEL="+str(model))
print("REPLY="+reply[:160])
print("EXACT_OK="+("YES" if reply == "OK" else "NO"))
PY
