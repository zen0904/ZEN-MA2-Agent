#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends wmctrl
echo "WMCTRL=$(command -v wmctrl)"
echo "WMCTRL_INSTALL=PASS"
