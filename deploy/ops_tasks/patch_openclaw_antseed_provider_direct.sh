#!/usr/bin/env bash
set -euo pipefail

OPENCLAW=/opt/node/bin/openclaw
export HOME=/root
export OPENCLAW_STATE_DIR=/root/.openclaw
export OPENCLAW_CONFIG_PATH=/root/.openclaw/openclaw.json
CFG="$OPENCLAW_CONFIG_PATH"

[[ -x "$OPENCLAW" ]] || { echo "openclaw missing" >&2; exit 70; }
mkdir -p /root/.openclaw
[[ -f "$CFG" ]] || { echo "OpenClaw config missing: $CFG" >&2; exit 71; }

before_default="$(mktemp)"
"$OPENCLAW" config get agents.defaults.model --json >"$before_default" 2>/dev/null || true

backup="$(mktemp /tmp/openclaw-antseed-backup.XXXXXX.json)"
cp -a "$CFG" "$backup"

python3 - "$CFG" <<'PY'
import json, os, sys, tempfile
from pathlib import Path

p = Path(sys.argv[1])
raw = p.read_text()
data = json.loads(raw)

models = data.setdefault("models", {})
models["mode"] = "merge"
providers = models.setdefault("providers", {})
providers["antseed"] = {
    "baseUrl": "http://127.0.0.1:8377/v1",
    "apiKey": "antseed-p2p",
    "authHeader": True,
    "api": "openai-completions",
    "models": [
        {
            "id": "deepseek-v4-flash",
            "name": "DeepSeek V4 Flash via Antseed",
            "reasoning": False,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 128000,
            "maxTokens": 8192,
        }
    ],
}

agents = data.setdefault("agents", {})
defaults = agents.setdefault("defaults", {})
visible = defaults.setdefault("models", {})
visible.setdefault("antseed/deepseek-v4-flash", {})

st = p.stat()
fd, tmp = tempfile.mkstemp(prefix=".openclaw.", suffix=".json", dir=str(p.parent))
os.close(fd)
Path(tmp).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
os.chmod(tmp, st.st_mode & 0o777)
os.chown(tmp, st.st_uid, st.st_gid)
os.replace(tmp, p)
PY

if ! "$OPENCLAW" config validate >/tmp/openclaw-antseed-validate.txt 2>&1; then
  cp -a "$backup" "$CFG"
  echo "VALIDATE=FAIL_ROLLED_BACK"
  sed -e 's#/root/.openclaw#<OPENCLAW_HOME>#g' /tmp/openclaw-antseed-validate.txt
  rm -f "$backup" "$before_default" /tmp/openclaw-antseed-validate.txt
  exit 72
fi
echo "VALIDATE=PASS"
sed -e 's#/root/.openclaw#<OPENCLAW_HOME>#g' /tmp/openclaw-antseed-validate.txt
rm -f /tmp/openclaw-antseed-validate.txt

after_default="$(mktemp)"
"$OPENCLAW" config get agents.defaults.model --json >"$after_default" 2>/dev/null || true
if ! cmp -s "$before_default" "$after_default"; then
  cp -a "$backup" "$CFG"
  echo "DEFAULT_MODEL_CHANGED=YES_ROLLED_BACK" >&2
  rm -f "$backup" "$before_default" "$after_default"
  exit 73
fi
rm -f "$before_default" "$after_default"

python3 - "$CFG" <<'PY'
import json, sys
p=json.load(open(sys.argv[1]))
prov=((p.get("models") or {}).get("providers") or {}).get("antseed") or {}
mods=prov.get("models") or []
vis=(((p.get("agents") or {}).get("defaults") or {}).get("models") or {})
print("PROVIDER_PRESENT=" + ("YES" if prov else "NO"))
print("BASE_URL=" + str(prov.get("baseUrl")))
print("API=" + str(prov.get("api")))
print("AUTH_HEADER=" + str(prov.get("authHeader")))
print("MODEL_IDS=" + ",".join(str(x.get("id")) for x in mods if isinstance(x,dict) and x.get("id")))
print("VISIBLE_ENTRY=" + ("YES" if "antseed/deepseek-v4-flash" in vis else "NO"))
print("DEFAULT_MODEL_UNCHANGED=YES")
PY

echo "=== models list ==="
"$OPENCLAW" models list 2>&1 | grep -Ei 'antseed|deepseek-v4-flash' || true

rm -f "$backup"
echo "ANTSEED_OPENCLAW_CONFIG=PASS"
echo "ANTSEED_PROVIDER_DEFAULT=NO"
