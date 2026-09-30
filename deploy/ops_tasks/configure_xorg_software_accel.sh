#!/usr/bin/env bash
set -euo pipefail

install -d -m 0755 /etc/X11/xorg.conf.d
cat >/etc/X11/xorg.conf.d/20-zen-intel-software.conf <<'EOF'
Section "Device"
    Identifier "ZEN Intel Graphics"
    Driver "modesetting"
    Option "AccelMethod" "none"
EndSection
EOF
chmod 0644 /etc/X11/xorg.conf.d/20-zen-intel-software.conf

echo "XORG_GLAMOR_DISABLED=YES"
echo "XORG_CONFIG=/etc/X11/xorg.conf.d/20-zen-intel-software.conf"
