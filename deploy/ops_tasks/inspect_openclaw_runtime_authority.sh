#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus

echo '=== systemd user unit authority ==='
systemctl --user show openclaw-gateway.service -p FragmentPath -p SourcePath -p WorkingDirectory -p ExecStart -p Environment --no-pager > /tmp/zen-openclaw-show.txt 2>&1 || true
python3 - <<'PY'
from pathlib import Path
p=Path('/tmp/zen-openclaw-show.txt')
if not p.exists(): raise SystemExit
for raw in p.read_text(errors='replace').splitlines():
    if raw.startswith(('FragmentPath=','SourcePath=','WorkingDirectory=','ExecStart=')):
        line=raw.replace('/root/.openclaw','<ROOT_OPENCLAW>').replace('/root/','<ROOT>/')
        print(line)
    elif raw.startswith('Environment='):
        body=raw[len('Environment='):]
        parts=[]
        for tok in body.split():
            key=tok.split('=',1)[0].strip('"') if '=' in tok else tok
            if key in {'HOME','OPENCLAW_HOME','OPENCLAW_CONFIG_PATH','OPENCLAW_STATE_DIR','OPENCLAW_PROFILE','XDG_CONFIG_HOME','PATH'}:
                if key=='PATH': parts.append('PATH=<SET>')
                else:
                    v=tok.replace('/root/.openclaw','<ROOT_OPENCLAW>').replace('/root/','<ROOT>/')
                    parts.append(v)
        print('EnvironmentSafe='+' '.join(parts))
PY
rm -f /tmp/zen-openclaw-show.txt

echo '=== gateway safe env ==='
pid="$(pgrep -f 'openclaw/dist/index.js gateway --port 18789' | head -n1 || true)"
if [[ -n "$pid" ]]; then
python3 - "$pid" <<'PY'
import sys
pid=sys.argv[1]
raw=open(f'/proc/{pid}/environ','rb').read().split(b'\0')
want={'HOME','OPENCLAW_HOME','OPENCLAW_CONFIG_PATH','OPENCLAW_STATE_DIR','OPENCLAW_PROFILE','XDG_CONFIG_HOME','PWD'}
vals={}
for item in raw:
    if b'=' not in item: continue
    k,v=item.split(b'=',1); k=k.decode(errors='replace')
    if k in want:
        val=v.decode(errors='replace').replace('/root/.openclaw','<ROOT_OPENCLAW>').replace('/root/','<ROOT>/')
        vals[k]=val
for k in sorted(want): print(k+'='+vals.get(k,'<UNSET>'))
PY
else
  echo GATEWAY_PID=NONE
fi

echo '=== bounded config search ==='
python3 - <<'PY'
from pathlib import Path
roots=[Path('/root'),Path('/var/lib/zen-openclaw'),Path('/opt/zen')]
seen=[]
for root in roots:
    if not root.exists(): continue
    try:
        for p in root.rglob('openclaw.json'):
            s=str(p)
            if any(x in s for x in ('/.ssh/','/node_modules/','/.cache/')): continue
            parts=p.relative_to(root).parts
            if len(parts)>5: continue
            seen.append(s)
    except Exception:
        pass
for s in sorted(set(seen)):
    print(s.replace('/root/.openclaw','<ROOT_OPENCLAW>').replace('/root/','<ROOT>/'))
print('CONFIG_MATCH_COUNT='+str(len(set(seen))))
PY
