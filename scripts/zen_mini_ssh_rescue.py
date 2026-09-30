#!/usr/bin/env python3
"""Bounded Windows -> Mini SSH rescue for the ZEN Ops private-repo lane.

This script never accepts, prints, or transports a GitHub token.  It reuses an
already-working root GitHub CLI login on the Mini, hydrates a dedicated
/var/lib/zen-ops/gh credential store for services that retain ProtectHome=true,
then reconciles the canonical updater/worker/result plane.

MA2_WRITES=0 / MA3_WRITES=0 by construction: only Mini maintenance services,
Git metadata, tmux control-room reconciliation, and the optional GitHub Actions
runner service are touched.
"""
from __future__ import annotations

import subprocess
import sys

MINI = "root@100.122.169.17"

REMOTE_SCRIPT = r"""set -euo pipefail

echo "HOST=$(hostname)"
echo "RESCUE=ZEN_MINI_PRIVATE_REPO_AUTH"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

if ! command -v gh >/dev/null 2>&1; then
  echo "GH_CLI=ABSENT"
  exit 20
fi

if ! gh auth status --hostname github.com >/tmp/zen-gh-auth-status.txt 2>&1; then
  echo "EXISTING_ROOT_GH_AUTH=NO"
  sed -n '1,40p' /tmp/zen-gh-auth-status.txt
  rm -f /tmp/zen-gh-auth-status.txt
  exit 21
fi
rm -f /tmp/zen-gh-auth-status.txt
echo "EXISTING_ROOT_GH_AUTH=YES"

token="$(gh auth token --hostname github.com 2>/dev/null || true)"
if [[ -z "$token" ]]; then
  echo "EXISTING_ROOT_GH_TOKEN=UNAVAILABLE"
  exit 22
fi

install -d -m 0700 /var/lib/zen-ops/gh
printf '%s\n' "$token" | GH_CONFIG_DIR=/var/lib/zen-ops/gh gh auth login   --hostname github.com --git-protocol https --with-token >/dev/null 2>&1
unset token
chmod 0700 /var/lib/zen-ops/gh
[[ -f /var/lib/zen-ops/gh/hosts.yml ]] && chmod 0600 /var/lib/zen-ops/gh/hosts.yml
echo "DEDICATED_GH_STORE=READY"

R=/opt/zen/zen-ops-runtime
if [[ ! -d "$R/.git" ]]; then
  echo "OPS_RUNTIME_GIT=ABSENT"
  exit 23
fi

export GH_CONFIG_DIR=/var/lib/zen-ops/gh
export GIT_TERMINAL_PROMPT=0
git -C "$R" config credential.helper '!/usr/bin/gh auth git-credential'
if ! git -C "$R" ls-remote --exit-code origin HEAD >/dev/null 2>&1; then
  echo "PRIVATE_REPO_READ=FAIL"
  exit 24
fi
echo "PRIVATE_REPO_READ=PASS"

git -C "$R" fetch -q --depth 1 origin main
git -C "$R" reset -q --hard origin/main
echo "OPS_RUNTIME_HEAD=$(git -C "$R" rev-parse --short HEAD)"

install -m 0755 "$R/deploy/ubuntu/zen-ops-update" /usr/local/sbin/zen-ops-update
GH_CONFIG_DIR=/var/lib/zen-ops/gh /usr/local/sbin/zen-ops-update

# The Actions runner is a backup/diagnostic lane.  Revive only a repo/host
# matching runner when present; it never becomes the canonical Ops authority.
mapfile -t runner_units < <(
  systemctl list-unit-files 'actions.runner*.service' --no-legend 2>/dev/null |
  awk '{print $1}' |
  grep -Ei 'ZEN[-_.]?MA2[-_.]?Agent|zen[-_.]?mini|zen[-_.]?agent[-_.]?server' || true
)
if [[ "${#runner_units[@]}" -eq 0 ]]; then
  mapfile -t all_runner_units < <(
    systemctl list-unit-files 'actions.runner*.service' --no-legend 2>/dev/null |
    awk '{print $1}'
  )
  if [[ "${#all_runner_units[@]}" -eq 1 ]]; then
    runner_units=("${all_runner_units[0]}")
  fi
fi
for unit in "${runner_units[@]}"; do
  systemctl enable "$unit" >/dev/null 2>&1 || true
  systemctl restart "$unit" || true
  echo "ACTIONS_RUNNER_UNIT=$unit"
  echo "ACTIONS_RUNNER_STATE=$(systemctl is-active "$unit" 2>/dev/null || true)"
done
if [[ "${#runner_units[@]}" -eq 0 ]]; then
  echo "ACTIONS_RUNNER_UNIT=NOT_FOUND"
fi

bash "$R/deploy/ops_tasks/verify_zen_ops_recovery.sh"
echo "RESCUE_COMPLETE=PASS"
"""

def main() -> int:
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=12",
        "-o", "StrictHostKeyChecking=accept-new",
        MINI,
        "bash -s",
    ]
    proc = subprocess.run(
        cmd,
        input=REMOTE_SCRIPT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
        check=False,
    )
    print(proc.stdout.rstrip())
    print(f"SSH_RETURN_CODE={proc.returncode}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
