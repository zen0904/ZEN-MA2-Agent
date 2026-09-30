#!/usr/bin/env bash
set -euo pipefail

CODEX=/usr/local/bin/codex
[[ -x "$CODEX" ]] || { echo "CODEX_MISSING"; exit 70; }
command -v tmux >/dev/null 2>&1 || { echo "TMUX_MISSING"; exit 71; }

session="$(tmux list-clients -F '#{client_session}' 2>/dev/null | head -n1 || true)"
if [[ -z "$session" ]]; then
  session="$(tmux list-sessions -F '#S' 2>/dev/null | head -n1 || true)"
fi

if [[ -z "$session" ]]; then
  session="codex-auth"
  tmux new-session -d -s "$session" -n "codex-login"
else
  if tmux list-windows -t "$session" -F '#W' | grep -Fxq 'codex-login'; then
    tmux kill-window -t "$session:codex-login" || true
  fi
  tmux new-window -d -t "$session" -n "codex-login"
fi

tmux send-keys -t "$session:codex-login" "clear" C-m
tmux send-keys -t "$session:codex-login" "echo 'CODEX DEVICE LOGIN - use your phone to open the URL shown below and enter the one-time code. Do not share that code.'" C-m
tmux send-keys -t "$session:codex-login" "echo" C-m
tmux send-keys -t "$session:codex-login" "exec /usr/local/bin/codex login --device-auth" C-m

# Bring the login window to the currently attached console without copying any
# device code into the ZEN Ops public result channel.
tmux select-window -t "$session:codex-login" 2>/dev/null || true

echo "CODEX_DEVICE_AUTH_STARTED=YES"
echo "TMUX_SESSION=$session"
echo "TMUX_WINDOW=codex-login"
echo "DEVICE_CODE_EXPOSED_TO_OPS=NO"
