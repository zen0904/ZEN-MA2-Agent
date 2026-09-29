#!/usr/bin/env bash
set -euo pipefail

ANTSEED=/usr/local/bin/zen-antseed
OPENCLAW=/opt/node/bin/openclaw
ANT_HOME=/var/lib/zen-antseed
MODEL=deepseek-v4-flash

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
before="$("$OPENCLAW" config get agents.defaults.model --json 2>/dev/null || true)"
provider='{"baseUrl":"http://127.0.0.1:8377/v1","apiKey":"antseed-p2p","authHeader":true,"api":"openai-completions","models":[{"id":"deepseek-v4-flash","name":"DeepSeek V4 Flash via Antseed","reasoning":false,"input":["text"],"contextWindow":128000,"maxTokens":8192}]}'
if "$OPENCLAW" config get models.providers.antseed --json >/tmp/zen-antseed-openclaw-provider.json 2>/dev/null; then
  "$OPENCLAW" config set models.providers.antseed.baseUrl '"http://127.0.0.1:8377/v1"' --strict-json
  "$OPENCLAW" config set models.providers.antseed.apiKey '"antseed-p2p"' --strict-json
  "$OPENCLAW" config set models.providers.antseed.authHeader true --strict-json
  "$OPENCLAW" config set models.providers.antseed.api '"openai-completions"' --strict-json
  if ! grep -q '"deepseek-v4-flash"' /tmp/zen-antseed-openclaw-provider.json; then
    "$OPENCLAW" config set models.providers.antseed.models '[{"id":"deepseek-v4-flash","name":"DeepSeek V4 Flash via Antseed","reasoning":false,"input":["text"],"contextWindow":128000,"maxTokens":8192}]' --strict-json --merge
  fi
else
  "$OPENCLAW" config set models.providers.antseed "$provider" --strict-json --expect-current-absent
fi
rm -f /tmp/zen-antseed-openclaw-provider.json
"$OPENCLAW" config set agents.defaults.models '{"antseed/deepseek-v4-flash":{}}' --strict-json --merge

after="$("$OPENCLAW" config get agents.defaults.model --json 2>/dev/null || true)"
[[ "$before" == "$after" ]] || {
  echo "DEFAULT_MODEL_CHANGED_UNEXPECTEDLY" >&2
  exit 72
}

echo "=== OpenClaw verification ==="
"$OPENCLAW" config get models.providers.antseed --json
"$OPENCLAW" models list | grep -i 'antseed\|deepseek-v4-flash' || true
echo "DEFAULT_MODEL_UNCHANGED=YES"
echo "ANTSEED_PROVIDER_REGISTERED=YES"
echo "ANTSEED_PROVIDER_DEFAULT=NO"
echo "ANTSEED_FREE_ONLY=YES"
