#!/usr/bin/env bash
set -euo pipefail

unit="zen-controlled-reboot-$(date +%s)"
echo "REBOOT_UNIT=$unit"
systemd-run --unit="$unit" --on-active=8s /usr/bin/systemctl reboot
echo "REBOOT_SCHEDULED=YES"
echo "DELAY_SECONDS=8"
