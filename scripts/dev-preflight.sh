#!/usr/bin/env bash
set -euo pipefail

busy=0
for port in "$@"; do
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "ReplayTutor cannot start: port $port is already in use."
    lsof -nP -iTCP:"$port" -sTCP:LISTEN
    echo "Stop that process, or run 'kill <PID>' after confirming it is safe."
    busy=1
  fi
done
exit "$busy"
