#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y --no-install-recommends   xserver-xorg-core xinit openbox dbus-x11 x11-xserver-utils xfonts-base

GUI_USER=zenui
GUI_HOME=/var/lib/zenui

if ! id "$GUI_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$GUI_HOME" --shell /bin/bash "$GUI_USER"
else
  usermod -d "$GUI_HOME" "$GUI_USER" || true
fi
install -d -o "$GUI_USER" -g "$GUI_USER" -m 0700 "$GUI_HOME" "$GUI_HOME/.config"

for g in video render audio; do
  getent group "$g" >/dev/null 2>&1 && usermod -aG "$g" "$GUI_USER" || true
done

install -d -m 0755 /usr/local/libexec
cat >/usr/local/libexec/zen-chatgpt-session.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:0
xsetroot -solid '#202124' || true
xhost +SI:localuser:zenui >/dev/null 2>&1 || true
exec runuser -u zenui -- env   HOME=/var/lib/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_SESSION_TYPE=x11   XDG_CONFIG_HOME=/var/lib/zenui/.config   dbus-run-session -- bash -lc '
    openbox-session >/var/lib/zenui/openbox.log 2>&1 &
    sleep 1
    exec /usr/bin/chatgpt
  '
EOF
chmod 0755 /usr/local/libexec/zen-chatgpt-session.sh

echo "CHATGPT_GUI_RUNTIME=PASS"
echo "GUI_USER=$GUI_USER"
echo "GUI_HOME=$GUI_HOME"
echo "XORG=$(command -v Xorg)"
echo "OPENBOX=$(command -v openbox-session)"
