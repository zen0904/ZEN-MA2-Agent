#!/usr/bin/env bash
set -euo pipefail

install -d -m 0755 /var/lib/zen-ops/public
printf 'ROOT_TASK_OK\n' > /var/lib/zen-ops/public/root-proof.txt
printf 'ROOT_TASK_OK\n'
id
systemctl is-active zen-ops-worker.service
