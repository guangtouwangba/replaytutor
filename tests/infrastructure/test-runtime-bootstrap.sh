#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

pnpm_version="$(env PATH=/usr/bin:/bin "$project_root/scripts/pnpm" --version)"
uv_version="$(env PATH=/usr/bin:/bin "$project_root/scripts/uv" --version)"

test "$pnpm_version" = "11.9.0"
case "$uv_version" in
  "uv "*) ;;
  *)
    echo "unexpected uv version output: $uv_version" >&2
    exit 1
    ;;
esac

echo "runtime bootstrap works with a minimal PATH"
