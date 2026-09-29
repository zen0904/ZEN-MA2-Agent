#!/usr/bin/env bash
set -euo pipefail

OPENCLAW=/opt/node/bin/openclaw

sanitize_path() {
  sed -e 's#/root/.openclaw#<OPENCLAW_HOME>#g' \
      -e 's#/root/.clawdbot#<LEGACY_OPENCLAW_HOME>#g' \
      -e 's#/var/lib/zen-ops/.openclaw#<ZENOPS_OPENCLAW_HOME>#g'
}

echo "=== CLI config file ==="
"$OPENCLAW" config file 2>&1 | sanitize_path || true

echo "=== candidate presence ==="
for spec in \
  "NEW:/root/.openclaw/openclaw.json" \
  "LEGACY:/root/.clawdbot/openclaw.json" \
  "ZENOPS:/var/lib/zen-ops/.openclaw/openclaw.json"; do
  label="${spec%%:*}"
  p="${spec#*:}"
  if [[ -f "$p" ]]; then
    echo "${label}_EXISTS=YES"
  else
    echo "${label}_EXISTS=NO"
  fi
done

echo "=== gateway selected env keys ==="
pid="$(pgrep -f 'openclaw/dist/index.js gateway --port 18789' | head -n1 || true)"
if [[ -z "$pid" ]]; then
  echo "GATEWAY_PID=NONE"
  exit 0
fi
echo "GATEWAY_PID_PRESENT=YES"
python3 - "$pid" <<'PY'
import sys
pid=sys.argv[1]
raw=open(f"/proc/{pid}/environ","rb").read().split(b"\0")
want={"HOME","OPENCLAW_CONFIG_PATH","OPENCLAW_STATE_DIR","OPENCLAW_PROFILE"}
vals={}
for item in raw:
    if b"=" not in item:
        continue
    k,v=item.split(b"=",1)
    key=k.decode(errors="replace")
    if key in want:
        val=v.decode(errors="replace")
        val=val.replace("/root/.openclaw","<OPENCLAW_HOME>")
        val=val.replace("/root/.clawdbot","<LEGACY_OPENCLAW_HOME>")
        val=val.replace("/var/lib/zen-ops/.openclaw","<ZENOPS_OPENCLAW_HOME>")
        vals[key]=val
for key in sorted(want):
    print(f"{key}="+vals.get(key,"<UNSET>"))
PY
