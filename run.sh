#!/usr/bin/env bash
# Start the bot in the background with nohup, without systemd.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Virtual environment not found. Run:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

source .venv/bin/activate

if [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  echo "Bot already running with PID $(cat bot.pid)"
  exit 0
fi

mkdir -p logs
nohup python3 run.py >> logs/stdout.log 2>&1 &
echo $! > bot.pid
echo "Bot started with PID $(cat bot.pid). Logs: logs/stdout.log and logs/bot.log"
