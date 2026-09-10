#!/usr/bin/env bash
# Stop the bot process started by run.sh.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f "bot.pid" ]; then
  echo "No bot.pid file found. Is the bot running?"
  exit 1
fi

PID="$(cat bot.pid)"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Sent SIGTERM to PID $PID"
  sleep 1
  if kill -0 "$PID" 2>/dev/null; then
    echo "Process still alive, sending SIGKILL"
    kill -9 "$PID" || true
  fi
else
  echo "Process $PID not running."
fi
rm -f bot.pid
