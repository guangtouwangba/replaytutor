#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runtime_bin="$(mktemp -d)"
trap 'rm -f "$runtime_bin/node" "$runtime_bin/corepack" "$runtime_bin/uv"; rmdir "$runtime_bin"' EXIT

# GitHub setup actions install tools outside /usr/bin, while local nvm installs
# them under a user-specific directory. Build the same deliberately small PATH
# from the runtimes resolved by the calling environment so the assertion stays
# portable across both layouts.
ln -s "$(command -v node)" "$runtime_bin/node"
ln -s "$(command -v corepack)" "$runtime_bin/corepack"
ln -s "$(command -v uv)" "$runtime_bin/uv"
minimal_path="$runtime_bin:/usr/bin:/bin"

pnpm_version="$(env PATH="$minimal_path" "$project_root/scripts/pnpm" --version)"
uv_version="$(env PATH="$minimal_path" "$project_root/scripts/uv" --version)"

test "$pnpm_version" = "11.9.0"
case "$uv_version" in
  "uv "*) ;;
  *)
    echo "unexpected uv version output: $uv_version" >&2
    exit 1
    ;;
esac

echo "runtime bootstrap works with a minimal PATH"
