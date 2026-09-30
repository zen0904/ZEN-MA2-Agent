#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y --no-install-recommends   xserver-xorg-core xinit openbox dbus-x11 x11-xserver-utils xfonts-base

if ! id zenui >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash zenui
fi
for g in video render audio; do
  getent group "$g" >/dev/null 2>&1 && usermod -aG "$g" zenui || true
done

install -d -o zenui -g zenui -m 0700 /home/zenui/.config

cat >/usr/local/libexec/zen-chatgpt-session.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:0
xsetroot -solid '#202124' || true
xhost +SI:localuser:zenui >/dev/null 2>&1 || true
exec runuser -u zenui -- env   HOME=/home/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_SESSION_TYPE=x11   dbus-run-session -- bash -lc '
    openbox-session >/tmp/zenui-openbox.log 2>&1 &
    sleep 1
    exec /usr/bin/chatgpt
  '
EOF
chmod 0755 /usr/local/libexec/zen-chatgpt-session.sh

echo "CHATGPT_GUI_RUNTIME=PASS"
echo "GUI_USER=zenui"
echo "XORG=$(command -v Xorg)"
echo "OPENBOX=$(command -v openbox-session)"
