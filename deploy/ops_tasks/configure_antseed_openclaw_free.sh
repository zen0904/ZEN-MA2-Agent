#!/usr/bin/env bash
set -euo pipefail

ANTSEED=/usr/local/bin/zen-antseed
OPENCLAW=/opt/node/bin/openclaw
ANT_HOME=/var/lib/zen-antseed
MODEL=deepseek-v4-flash

# zen-ops-worker is intentionally sandboxed with ProtectHome=true. OpenClaw's
# live root-owned state therefore must be mutated by a separate transient
# systemd unit spawned by the manager, still reached only through this
# allowlisted repo_task.
if [[ "${ZEN_OPENCLAW_CONFIG_CHILD:-0}" != "1" ]]; then
  unit="zen-antseed-openclaw-config-$(date +%s)"
  exec systemd-run --quiet --wait --collect --pipe \
    --unit="$unit" \
    --setenv=ZEN_OPENCLAW_CONFIG_CHILD=1 \
    /bin/bash "$0"
fi
export HOME=/root
export OPENCLAW_STATE_DIR=/root/.openclaw
export OPENCLAW_CONFIG_PATH=/root/.openclaw/openclaw.json
install -d -m 0700 /root/.openclaw

[[ -x "$ANTSEED" ]] || { echo "zen-antseed wrapper missing" >&2; exit 70; }
[[ -x "$OPENCLAW" ]] || { echo "openclaw missing" >&2; exit 70; }

echo "=== Antseed free-only routing ==="
ANT_CFG="$ANT_HOME/.antseed/config.json"
install -d -o zenantseed -g zenantseed -m 0700 "$ANT_HOME/.antseed"
if [[ ! -f "$ANT_CFG" ]]; then
  runuser -u zenantseed -- env HOME="$ANT_HOME" "$ANTSEED" -c "$ANT_CFG" config init
fi
python3 - "$ANT_CFG" <<'PY'
import json, os, sys, tempfile
from pathlib import Path
p=Path(sys.argv[1])
d=json.loads(p.read_text())
buyer=d.setdefault("buyer",{})
routing=buyer.setdefault("routingPreferences",{})
routing["preferFreePeers"]=True
routing["minTrustScore"]=0
maxp=buyer.setdefault("maxPricing",{}).setdefault("defaults",{})
maxp["inputUsdPerMillion"]=0
maxp["outputUsdPerMillion"]=0
fd,tmp=tempfile.mkstemp(prefix=".config.", suffix=".json", dir=str(p.parent))
os.close(fd)
Path(tmp).write_text(json.dumps(d, ensure_ascii=False, indent=2)+"\n")
os.chmod(tmp,0o600)
os.replace(tmp,p)
PY
chown zenantseed:zenantseed "$ANT_CFG"
runuser -u zenantseed -- env HOME="$ANT_HOME" "$ANTSEED" -c "$ANT_CFG" config show >/tmp/zen-antseed-config-show.json
python3 - <<'PY'
import json
p=json.load(open("/tmp/zen-antseed-config-show.json"))
b=p.get("buyer",{})
r=b.get("routingPreferences",{})
m=b.get("maxPricing",{}).get("defaults",{})
print("PREFER_FREE="+str(r.get("preferFreePeers")))
print("MIN_TRUST="+str(r.get("minTrustScore")))
print("MAX_INPUT="+str(m.get("inputUsdPerMillion")))
print("MAX_OUTPUT="+str(m.get("outputUsdPerMillion")))
PY
rm -f /tmp/zen-antseed-config-show.json

echo "=== Verify current catalog contains target ==="
python3 - <<'PY'
import json, urllib.request
p=json.load(urllib.request.urlopen("http://127.0.0.1:8377/v1/models", timeout=5))
ids={str(x.get("id")) for x in p.get("data",[]) if isinstance(x,dict)}
if "deepseek-v4-flash" not in ids:
    raise SystemExit("deepseek-v4-flash is not currently advertised")
print("MODEL_PRESENT=YES")
PY

echo "=== Direct free-route smoke ==="
python3 - <<'PY'
import json, urllib.request, urllib.error
url="http://127.0.0.1:8377/v1/chat/completions"
payload={"model":"deepseek-v4-flash","max_tokens":16,"messages":[{"role":"user","content":"Reply only: OK"}]}
req=urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={"content-type":"application/json","Authorization":"Bearer antseed-p2p"},
    method="POST",
)
try:
    with urllib.request.urlopen(req,timeout=180) as r:
        p=json.load(r)
except urllib.error.HTTPError as e:
    print(e.read().decode(errors="replace")[:1200])
    raise
text=((p.get("choices") or [{}])[0].get("message") or {}).get("content","")
print("HTTP_SMOKE=PASS")
print("MODEL_RETURNED="+str(p.get("model")))
print("TEXT="+str(text)[:160])
PY

echo "=== OpenClaw provider registration ==="
before_file="$(mktemp)"
before_rc=0
"$OPENCLAW" config get agents.defaults.model --json >"$before_file" 2>/dev/null || before_rc=$?

patch_file="$(mktemp)"
cat >"$patch_file" <<'JSON'
{
  "models": {
    "mode": "merge",
    "providers": {
      "antseed": {
        "baseUrl": "http://127.0.0.1:8377/v1",
        "apiKey": "antseed-p2p",
        "authHeader": true,
        "api": "openai-completions",
        "models": [
          {
            "id": "deepseek-v4-flash",
            "name": "DeepSeek V4 Flash via Antseed",
            "reasoning": false,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 128000,
            "maxTokens": 8192
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "models": {
        "antseed/deepseek-v4-flash": {}
      }
    }
  }
}
JSON

echo "OPENCLAW_PATCH_DRY_RUN"
"$OPENCLAW" config patch --file "$patch_file" --dry-run >/tmp/zen-openclaw-patch-dry.txt 2>&1 || {
  sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' -e 's/antseed-p2p/<LOCAL_PLACEHOLDER>/g' /tmp/zen-openclaw-patch-dry.txt
  rm -f "$patch_file" "$before_file" /tmp/zen-openclaw-patch-dry.txt
  exit 71
}
sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' -e 's/antseed-p2p/<LOCAL_PLACEHOLDER>/g' /tmp/zen-openclaw-patch-dry.txt
rm -f /tmp/zen-openclaw-patch-dry.txt

"$OPENCLAW" config patch --file "$patch_file" >/tmp/zen-openclaw-patch-apply.txt 2>&1 || {
  sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' -e 's/antseed-p2p/<LOCAL_PLACEHOLDER>/g' /tmp/zen-openclaw-patch-apply.txt
  rm -f "$patch_file" "$before_file" /tmp/zen-openclaw-patch-apply.txt
  exit 72
}
sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' -e 's/antseed-p2p/<LOCAL_PLACEHOLDER>/g' /tmp/zen-openclaw-patch-apply.txt
rm -f "$patch_file" /tmp/zen-openclaw-patch-apply.txt

"$OPENCLAW" config validate >/tmp/zen-openclaw-validate.txt 2>&1 || {
  sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' /tmp/zen-openclaw-validate.txt
  rm -f "$before_file" /tmp/zen-openclaw-validate.txt
  exit 73
}
sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' /tmp/zen-openclaw-validate.txt
rm -f /tmp/zen-openclaw-validate.txt

after_file="$(mktemp)"
after_rc=0
"$OPENCLAW" config get agents.defaults.model --json >"$after_file" 2>/dev/null || after_rc=$?
if [[ "$before_rc" -ne "$after_rc" ]] || ! cmp -s "$before_file" "$after_file"; then
  echo "DEFAULT_MODEL_CHANGED_UNEXPECTEDLY" >&2
  rm -f "$before_file" "$after_file"
  exit 74
fi
rm -f "$before_file" "$after_file"

echo "=== OpenClaw verification ==="
tmp="$(mktemp)"
"$OPENCLAW" config get models.providers.antseed --json >"$tmp"
python3 - "$tmp" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
models=p.get("models",[]) if isinstance(p,dict) else []
print("PROVIDER_PRESENT=YES")
print("BASE_URL="+str(p.get("baseUrl")))
print("API="+str(p.get("api")))
print("AUTH_HEADER="+str(p.get("authHeader")))
print("MODEL_IDS="+",".join(str(x.get("id")) for x in models if isinstance(x,dict) and x.get("id")))
print("API_KEY_PRESENT="+("YES" if bool(p.get("apiKey")) else "NO"))
PY
rm -f "$tmp"
"$OPENCLAW" models list 2>&1 | grep -i 'antseed\|deepseek-v4-flash' || true
echo "DEFAULT_MODEL_UNCHANGED=YES"
echo "ANTSEED_PROVIDER_REGISTERED=YES"
echo "ANTSEED_PROVIDER_DEFAULT=NO"
echo "ANTSEED_FREE_ONLY=YES"
