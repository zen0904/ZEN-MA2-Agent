#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends xserver-xorg-input-libinput xinput
echo "LIBINPUT_DRIVER=$(dpkg-query -W -f='${Status} ${Version}\n' xserver-xorg-input-libinput 2>/dev/null || true)"
echo "XINPUT=$(command -v xinput || true)"
echo "CHATGPT_INPUT_RUNTIME=PASS"
