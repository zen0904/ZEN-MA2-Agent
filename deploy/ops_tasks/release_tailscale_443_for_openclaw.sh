#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

tailscale funnel status --json >"$tmp"

python3 - "$tmp" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p, encoding='utf-8'))
web=d.get("Web", {})
host="zen-agent-server.tail3e0394.ts.net"
def proxy(port):
    h=web.get(f"{host}:{port}", {}).get("Handlers", {})
    return h.get("/", {}).get("Proxy")
p10000=proxy(10000)
p443=proxy(443)
print(f"PORT10000_PROXY={p10000}")
print(f"PORT443_PROXY={p443}")
if p10000 != "http://127.0.0.1:18991":
    raise SystemExit("refusing: dedicated 10000 ZEN Ops Funnel is not verified")
if p443 != "http://127.0.0.1:18991":
    raise SystemExit("refusing: 443 is not the expected old ZEN Ops route")
PY

echo "=== remove only old 443 ZEN Ops Funnel ==="
tailscale funnel --yes --https=443 off

echo "=== remaining routes ==="
tailscale funnel status --json

echo "ZEN_OPS_FUNNEL_10000=PRESERVED"
echo "TAILSCALE_443=FREE_FOR_OPENCLAW"
