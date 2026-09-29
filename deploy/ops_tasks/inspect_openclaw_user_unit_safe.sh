#!/usr/bin/env bash
set -euo pipefail

UNIT=/root/.config/systemd/user/openclaw-gateway.service
echo "=== unit present ==="
[[ -f "$UNIT" ]] && echo UNIT_PRESENT=YES || { echo UNIT_PRESENT=NO; exit 0; }

echo "=== safe unit fields ==="
python3 - "$UNIT" <<'PY'
import sys
p=sys.argv[1]
for raw in open(p, errors='replace'):
    line=raw.strip()
    if line.startswith('ExecStart='):
        # Do not print inline credentials if a future unit ever gains them.
        toks=line.split()
        safe=[]
        skip=False
        for t in toks:
            low=t.lower()
            if skip:
                safe.append('<REDACTED>'); skip=False; continue
            if low in {'--token','--api-key','--password'}:
                safe.append(t); skip=True; continue
            if any(x in low for x in ('token=','api_key=','password=')):
                safe.append('<REDACTED>')
            else:
                safe.append(t)
        print(' '.join(safe))
    elif line.startswith('WorkingDirectory='):
        print(line)
    elif line.startswith('Environment='):
        body=line[len('Environment='):].strip().strip('"')
        key=body.split('=',1)[0] if '=' in body else body
        if key in {'HOME','OPENCLAW_HOME','OPENCLAW_CONFIG_PATH','OPENCLAW_STATE_DIR','OPENCLAW_PROFILE','XDG_CONFIG_HOME','PATH'}:
            if key == 'PATH': print('Environment=PATH=<SET>')
            else: print('Environment='+body)
PY

echo "=== root config candidates ==="
python3 - <<'PY'
from pathlib import Path
cands={
 'ROOT_NEW':Path('/root/.openclaw/openclaw.json'),
 'ROOT_LEGACY':Path('/root/.clawdbot/openclaw.json'),
 'ROOT_FLAT':Path('/openclaw.json'),
 'OPT_ZEN':Path('/opt/zen/openclaw.json'),
 'VAR_ZEN':Path('/var/lib/zen-openclaw/openclaw.json'),
}
for k,p in cands.items():
    print(k+'_EXISTS='+('YES' if p.is_file() else 'NO'))
PY
