#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
cd "$project_root"

locale="en-US"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --) shift ;;
    --locale) locale="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [[ "$locale" != "en-US" && "$locale" != "zh-CN" ]]; then
  echo "Locale must be en-US or zh-CN" >&2
  exit 2
fi

record_root="$(mktemp -d "${TMPDIR:-/tmp}/replaytutor-demo.XXXXXX")"
api_port=8791
web_port=5175
cleanup() {
  [[ -n "${api_pid:-}" ]] && kill "$api_pid" 2>/dev/null || true
  [[ -n "${web_pid:-}" ]] && kill "$web_pid" 2>/dev/null || true
  rm -rf "$record_root"
}
trap cleanup EXIT INT TERM

export REPLAYTUTOR_DATA_DIR="$record_root/data"
export REPLAYTUTOR_CORS_ORIGINS="http://127.0.0.1:$web_port"
./scripts/demo-prepare.sh >/dev/null
./scripts/uv run --project apps/api uvicorn replaytutor.main:app --host 127.0.0.1 --port "$api_port" >"$record_root/api.log" 2>&1 & api_pid=$!
VITE_API_BASE_URL="http://127.0.0.1:$api_port" ./scripts/pnpm --filter @replaytutor/web exec vite --host 127.0.0.1 --port "$web_port" --strictPort >"$record_root/web.log" 2>&1 & web_pid=$!
for _ in {1..60}; do curl -fsS "http://127.0.0.1:$api_port/api/v1/health" >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:$web_port" >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS "http://127.0.0.1:$api_port/api/v1/health" >/dev/null
curl -fsS "http://127.0.0.1:$web_port" >/dev/null
./scripts/uv run --project apps/api python apps/demo-video/scripts/record_demo.py --locale "$locale" --api-url "http://127.0.0.1:$api_port" --web-url "http://127.0.0.1:$web_port"
