#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/.." && pwd)"
cd "$project_root"

demo_data_dir="${REPLAYTUTOR_DATA_DIR:-data/demo}"
export REPLAYTUTOR_DATA_DIR="$demo_data_dir"
mkdir -p "$demo_data_dir/market/snapshots" "$demo_data_dir/imports" "$demo_data_dir/runtime/agent-runs" "$demo_data_dir/exports"
./scripts/uv run --project apps/api python -c 'from replaytutor.config import get_settings; from replaytutor.runtime import ensure_runtime_directories; from replaytutor.storage.database import upgrade_database; from replaytutor.modules.market_data.service import MarketDataService; settings=get_settings(); ensure_runtime_directories(settings); upgrade_database(settings); snapshot=MarketDataService(settings).load_golden_dataset(); print(f"Demo snapshot ready: {snapshot.snapshot_id}")'
