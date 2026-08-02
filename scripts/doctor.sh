#!/usr/bin/env bash
set -euo pipefail

failed=0
check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "ok   $1: $(command -v "$1")"
  else
    echo "fail $1: not found"
    failed=1
  fi
}

echo "ReplayTutor doctor"
check_command node
check_command git
check_command curl
[[ -x scripts/pnpm ]] && echo "ok   pnpm wrapper" || { echo "fail pnpm wrapper"; failed=1; }
[[ -x scripts/uv ]] && echo "ok   uv wrapper" || { echo "fail uv wrapper"; failed=1; }
[[ -r tests/fixtures/market/btcusdt-1m-2025-01.parquet ]] && echo "ok   bundled BTCUSDT dataset" || { echo "fail bundled BTCUSDT dataset"; failed=1; }
for port in 5173 8788; do
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "warn port $port is in use"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN | sed -n '2,4p'
  else
    echo "ok   port $port is available"
  fi
done
exit "$failed"
