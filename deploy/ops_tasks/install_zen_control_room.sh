#!/usr/bin/env bash
set -euo pipefail

R=/opt/zen/zen-ops-runtime
SESSION=zenmon

install -m 0755 "$R/deploy/ubuntu/zen-control-room" /usr/local/bin/zen-control-room
install -m 0755 "$R/deploy/ubuntu/zenmon" /usr/local/bin/zenmon
install -m 0755 "$R/deploy/ubuntu/zen-console-mode" /usr/local/bin/zen-console-mode

python3 -m py_compile /usr/local/bin/zen-control-room

echo "CONTROL_ROOM_INSTALL=PASS"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  if tmux list-windows -t "$SESSION" -F '#{window_name}' | grep -qx ROOM; then
    tmux respawn-pane -k -t "$SESSION:ROOM.0" /usr/local/bin/zen-control-room
  else
    tmux new-window -d -t "$SESSION" -n ROOM /usr/local/bin/zen-control-room
  fi

  tmux bind-key -n F10 select-window -t zenmon:ROOM
  tmux bind-key -n F11 select-window -t zenmon:MONITOR
  tmux bind-key -n F12 select-window -t zenmon:MA_AGENT
  tmux set-option -t "$SESSION" -g status-left ' ZEN | F10 ROOM F11 MON F12 MA '
  tmux select-window -t "$SESSION:ROOM"
  echo "TMUX_ROOM_LIVE=YES"
else
  echo "TMUX_ROOM_LIVE=NO_SESSION"
fi

echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
