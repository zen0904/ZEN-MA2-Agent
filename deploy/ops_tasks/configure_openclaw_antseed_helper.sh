#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
OPENCLAW=/opt/node/bin/openclaw
STATUS=/var/lib/zen-ops/openclaw-antseed-config-status.txt

exec > >(tee "$STATUS") 2>&1

[[ -x "$OPENCLAW" ]] || { echo OPENCLAW_BINARY=MISSING; exit 31; }
install -d -m 0700 /root/.openclaw

echo '=== config authority ==='
cfg="$($OPENCLAW config file 2>/dev/null | tail -n1)"
[[ -n "$cfg" ]] || { echo CONFIG_PATH=EMPTY; exit 32; }
case "$cfg" in
  /root/*) echo CONFIG_SCOPE=ROOT_HOME ;;
  *) echo CONFIG_SCOPE=OTHER_ABSOLUTE ;;
esac

before_default="$(mktemp)"
$OPENCLAW config get agents.defaults.model --json >"$before_default" 2>/dev/null || true

patch="$(mktemp)"
cat >"$patch" <<'JSON'
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

echo '=== dry run ==='
$OPENCLAW config patch --file "$patch" --dry-run

echo '=== apply ==='
$OPENCLAW config patch --file "$patch"
rm -f "$patch"

echo '=== validate ==='
$OPENCLAW config validate

after_default="$(mktemp)"
$OPENCLAW config get agents.defaults.model --json >"$after_default" 2>/dev/null || true
if ! cmp -s "$before_default" "$after_default"; then
  echo DEFAULT_MODEL_CHANGED=YES
  rm -f "$before_default" "$after_default"
  exit 33
fi
rm -f "$before_default" "$after_default"
echo DEFAULT_MODEL_UNCHANGED=YES

echo '=== provider verify ==='
tmp="$(mktemp)"
$OPENCLAW config get models.providers.antseed --json >"$tmp"
python3 - "$tmp" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
mods=p.get('models',[]) if isinstance(p,dict) else []
print('PROVIDER_PRESENT='+('YES' if p else 'NO'))
print('BASE_URL='+str(p.get('baseUrl')))
print('API='+str(p.get('api')))
print('AUTH_HEADER='+str(p.get('authHeader')))
print('MODEL_IDS='+','.join(str(x.get('id')) for x in mods if isinstance(x,dict) and x.get('id')))
print('API_KEY_PRESENT='+('YES' if bool(p.get('apiKey')) else 'NO'))
PY
rm -f "$tmp"

echo '=== model list ==='
$OPENCLAW models list 2>&1 | grep -Ei 'antseed|deepseek-v4-flash' || true

echo OPENCLAW_ANTSEED_CONFIG=PASS
echo OPENCLAW_ANTSEED_DEFAULT=NO
