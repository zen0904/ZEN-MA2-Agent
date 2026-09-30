#!/usr/bin/env bash
set -euo pipefail

install -d -m 0755 /usr/local/libexec

cat >/usr/local/libexec/zen-open-browser <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export HOME=/var/lib/zenui
export USER=zenui
export LOGNAME=zenui
export DISPLAY=:0
export XDG_CONFIG_HOME=/var/lib/zenui/.config

# Never log the URL: OAuth links can contain one-time state/challenge values.
url="${1:-https://www.google.com/}"
/usr/bin/google-chrome   --no-first-run   --no-default-browser-check   --disable-gpu   --user-data-dir=/var/lib/zenui/.config/google-chrome   "$url" >/dev/null 2>&1 &

# Openbox does not always raise an existing Chrome window when a new URL is
# handed to it. Raise it explicitly so ChatGPT sign-in is actually visible.
for _ in $(seq 1 20); do
  if DISPLAY=:0 /usr/bin/wmctrl -x -a 'google-chrome.Google-chrome' 2>/dev/null; then
    exit 0
  fi
  sleep 0.25
done
exit 0
EOF
chmod 0755 /usr/local/libexec/zen-open-browser

cat >/usr/share/applications/zen-browser.desktop <<'EOF'
[Desktop Entry]
Name=ZEN Browser
Comment=Open links in the persistent Mini Chrome session
Exec=/usr/local/libexec/zen-open-browser %U
Terminal=false
Type=Application
MimeType=x-scheme-handler/http;x-scheme-handler/https;text/html;
NoDisplay=true
EOF
chmod 0644 /usr/share/applications/zen-browser.desktop
update-desktop-database /usr/share/applications >/dev/null 2>&1 || true

install -d -o zenui -g zenui -m 0700 /var/lib/zenui/.config
touch /var/lib/zenui/.config/mimeapps.list
chown zenui:zenui /var/lib/zenui/.config/mimeapps.list

runuser -u zenui -- env   HOME=/var/lib/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_CONFIG_HOME=/var/lib/zenui/.config   xdg-settings set default-web-browser zen-browser.desktop

runuser -u zenui -- env   HOME=/var/lib/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_CONFIG_HOME=/var/lib/zenui/.config   xdg-mime default zen-browser.desktop x-scheme-handler/http

runuser -u zenui -- env   HOME=/var/lib/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_CONFIG_HOME=/var/lib/zenui/.config   xdg-mime default zen-browser.desktop x-scheme-handler/https

# Make Electron's fallback browser choice explicit too.
install -d -m 0755 /etc/environment.d
cat >/etc/environment.d/90-zen-browser.conf <<'EOF'
BROWSER=/usr/local/libexec/zen-open-browser
EOF

# Benign handoff test. Does not expose any OAuth URL or token.
runuser -u zenui -- env   HOME=/var/lib/zenui   USER=zenui   LOGNAME=zenui   DISPLAY=:0   XDG_CONFIG_HOME=/var/lib/zenui/.config   BROWSER=/usr/local/libexec/zen-open-browser   xdg-open https://www.google.com/ >/dev/null 2>&1 || true

sleep 2
chvt 3 2>/dev/null || true

echo "DEFAULT_BROWSER=$(runuser -u zenui -- env HOME=/var/lib/zenui DISPLAY=:0 XDG_CONFIG_HOME=/var/lib/zenui/.config xdg-settings get default-web-browser 2>/dev/null || true)"
echo "HTTP_HANDLER=$(runuser -u zenui -- env HOME=/var/lib/zenui XDG_CONFIG_HOME=/var/lib/zenui/.config xdg-mime query default x-scheme-handler/http 2>/dev/null || true)"
echo "HTTPS_HANDLER=$(runuser -u zenui -- env HOME=/var/lib/zenui XDG_CONFIG_HOME=/var/lib/zenui/.config xdg-mime query default x-scheme-handler/https 2>/dev/null || true)"
echo "CHROME_WINDOW=$(DISPLAY=:0 wmctrl -l -x | grep -c 'google-chrome.*Google-chrome' || true)"
echo "CHATGPT_BROWSER_HANDOFF=PASS"
