#!/usr/bin/env bash
set -u
OPENCLAW=/opt/node/bin/openclaw

safe_print() {
  sed -e 's#/root/\.openclaw#<OPENCLAW_HOME>#g' -e 's/antseed-p2p/<LOCAL_PLACEHOLDER>/g' -e 's/api_key/<API_KEY_FIELD>/gi'
}

echo "=== version ==="
"$OPENCLAW" --version 2>&1 | safe_print

echo "=== provider get ==="
tmp="$(mktemp)"
err="$(mktemp)"
if "$OPENCLAW" config get models.providers.antseed --json >"$tmp" 2>"$err"; then
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
else
  echo "PROVIDER_PRESENT=NO"
  cat "$err" | safe_print
fi
rm -f "$tmp" "$err"

echo "=== default model ==="
"$OPENCLAW" config get agents.defaults.model --json 2>&1 | safe_print || true

echo "=== visible antseed model entry ==="
tmp="$(mktemp)"
if "$OPENCLAW" config get agents.defaults.models --json >"$tmp" 2>/dev/null; then
  python3 - "$tmp" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
print("VISIBLE_ENTRY="+("YES" if isinstance(p,dict) and "antseed/deepseek-v4-flash" in p else "NO"))
PY
else
  echo "VISIBLE_ENTRY=UNKNOWN"
fi
rm -f "$tmp"

echo "=== models list filtered ==="
"$OPENCLAW" models list 2>&1 | grep -Ei 'antseed|deepseek-v4-flash|error|invalid' | safe_print || true

echo "=== config help ==="
"$OPENCLAW" config --help 2>&1 | head -80 | safe_print || true
