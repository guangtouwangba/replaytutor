#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
migration_data_dir="$(mktemp -d)"
trap 'rm -f "$migration_data_dir/app.db" "$migration_data_dir/app.db-shm" "$migration_data_dir/app.db-wal"; rmdir "$migration_data_dir"' EXIT

env REPLAYTUTOR_DATA_DIR="$migration_data_dir" make -C "$project_root" migrate

test -f "$migration_data_dir/app.db"
revision="$(
  env REPLAYTUTOR_DATA_DIR="$migration_data_dir" \
    "$project_root/scripts/uv" run --project "$project_root/apps/api" python -c \
    'from replaytutor.config import get_settings; from replaytutor.storage.database import inspect_database; status = inspect_database(get_settings()); assert status.migration_current == status.migration_head; print(status.migration_current)'
)"
test -n "$revision"

echo "make migrate respects ReplayTutor database configuration at $revision"
