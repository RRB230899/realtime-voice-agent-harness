#!/usr/bin/env bash
# Single-command test call: ./run.sh <scenario>
# Starts the bridge server if it isn't running, then places the call.
# Prereq: ngrok tunnel running and PUBLIC_URL set in .env (see README).
set -euo pipefail
cd "$(dirname "$0")"

SCENARIO="${1:?usage: ./run.sh <scenario>   (scenario keys: see app/scenarios.py)}"
PORT="$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2)"
PORT="${PORT:-8080}"

source .venv/bin/activate

if ! curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1; then
  echo "Starting bridge server on port ${PORT} (logs: server.log)..."
  nohup uvicorn app.server:app --port "${PORT}" >> server.log 2>&1 &
  for _ in $(seq 1 20); do
    curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1 && break
    sleep 0.5
  done
fi

python -m app.main --scenario "$SCENARIO"
