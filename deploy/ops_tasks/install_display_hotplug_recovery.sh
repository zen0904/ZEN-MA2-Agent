#!/usr/bin/env bash
set -euo pipefail

R=/opt/zen/zen-ops-runtime

echo "TASK=INSTALL_DISPLAY_HOTPLUG_RECOVERY"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"

install -m 0755   "$R/deploy/ubuntu/zen-display-hotplug-recover"   /usr/local/sbin/zen-display-hotplug-recover

install -m 0644   "$R/deploy/ubuntu/systemd/zen-display-hotplug.service"   /etc/systemd/system/zen-display-hotplug.service

install -d -m 0755 /etc/udev/rules.d
install -m 0644   "$R/deploy/ubuntu/udev/99-zen-display-hotplug.rules"   /etc/udev/rules.d/99-zen-display-hotplug.rules

systemctl daemon-reload
udevadm control --reload-rules

# Acceptance must run through the real systemd unit, not inside the ZEN Ops
# worker's PrivateTmp namespace, otherwise the host X11 socket is invisible.
: > /var/log/zen-display-hotplug.log
systemctl start zen-display-hotplug.service
systemctl is-active --quiet zen-display-hotplug.service || true

echo "=== SERVICE ==="
systemctl cat zen-display-hotplug.service
systemctl show zen-display-hotplug.service -p Result -p ExecMainStatus --no-pager
echo "=== UDEV RULE ==="
cat /etc/udev/rules.d/99-zen-display-hotplug.rules
echo "=== RECOVERY LOG ==="
cat /var/log/zen-display-hotplug.log

test "$(systemctl show zen-display-hotplug.service -p Result --value)" = "success"
grep -q 'EVENT=complete' /var/log/zen-display-hotplug.log
grep -q 'LAYOUT=PASS' /var/log/zen-display-hotplug.log

echo "DISPLAY_HOTPLUG_RECOVERY=PASS"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
