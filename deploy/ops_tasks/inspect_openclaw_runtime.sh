#!/usr/bin/env bash
set -euo pipefail

echo "=== identity ==="
id
date -Is

echo "=== openclaw binary ==="
command -v openclaw || true
openclaw --version 2>&1 || true

echo "=== services ==="
systemctl list-unit-files --type=service --no-pager 2>/dev/null | grep -Ei 'openclaw|claw' || true
systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -Ei 'openclaw|claw' || true

echo "=== listeners ==="
ss -ltnp 2>/dev/null | grep -E ':18789 ' || true

echo "=== processes ==="
ps -ef | grep -Ei '[o]penclaw|18789' || true

echo "=== candidate state/config paths ==="
find /root /home /var/lib /opt/zen \
  \( -path '*/node_modules' -o -path '*/.git' -o -path '*/npm-cache' \) -prune -o \
  \( -iname '.openclaw' -o -iname '.openclaw-*' -o -iname 'openclaw.json' -o -iname 'openclaw*.json' -o -iname '*openclaw*.toml' -o -iname '*openclaw*.yaml' -o -iname '*openclaw*.yml' \) \
  -print 2>/dev/null | head -300

echo "=== candidate ownership ==="
while IFS= read -r p; do
  stat -c '%U:%G %a %n' "$p" 2>/dev/null || true
done < <(
  find /root /home /var/lib /opt/zen \
    \( -path '*/node_modules' -o -path '*/.git' -o -path '*/npm-cache' \) -prune -o \
    \( -iname '.openclaw' -o -iname '.openclaw-*' -o -iname 'openclaw.json' \) -print 2>/dev/null | head -120
)

echo "=== user systemd refs ==="
find /root /home -path '*/.config/systemd/user/*' -type f -maxdepth 7 -print 2>/dev/null | while read -r f; do
  if grep -qiE 'openclaw|18789' "$f"; then
    echo "--- $f"
    grep -nEi 'ExecStart|Environment|openclaw|18789|WantedBy|WorkingDirectory' "$f" 2>/dev/null || true
  fi
done

echo "=== system startup refs ==="
grep -RniE 'openclaw|18789' /etc/systemd/system /usr/lib/systemd/system /etc/cron.d /etc/rc.local 2>/dev/null | head -250 || true

echo "=== safe config summary ==="
python3 - <<'PY'
import json, os, glob
paths = []
for pat in [
    '/root/.openclaw/openclaw.json',
    '/root/.openclaw-*/openclaw.json',
    '/home/*/.openclaw/openclaw.json',
    '/home/*/.openclaw-*/openclaw.json',
    '/var/lib/**/openclaw.json',
    '/opt/zen/**/openclaw.json',
]:
    paths += glob.glob(pat, recursive=True)
for p in sorted(set(paths)):
    try:
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except Exception as e:
        print(f'{p}: unreadable_or_nonjson={type(e).__name__}')
        continue
    out = {'path': p}
    for key in ('gateway','plugins','agents'):
        v = d.get(key)
        if key == 'gateway' and isinstance(v, dict):
            out['gateway'] = {k:v.get(k) for k in ('mode','bind','port') if k in v}
        elif key == 'plugins' and isinstance(v, dict):
            out['plugins_keys'] = sorted(v.keys())
        elif key == 'agents':
            if isinstance(v, dict):
                out['agents_keys'] = sorted(v.keys())
            elif isinstance(v, list):
                out['agents_count'] = len(v)
    print(json.dumps(out, ensure_ascii=False))
PY

echo "=== daemon help ==="
openclaw daemon --help 2>&1 | head -180 || true
