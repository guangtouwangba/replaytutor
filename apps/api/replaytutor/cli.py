from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from replaytutor.config import get_settings
from replaytutor.contract_generation import check_contracts, export_contracts


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="replaytutor")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("api", help="start the local API")
    contracts = commands.add_parser("contracts", help="manage generated contracts")
    contracts.add_argument("action", choices=("check", "export"))
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "api":
        settings = get_settings()
        uvicorn.run(
            "replaytutor.main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=True,
            reload_dirs=[str(Path(__file__).resolve().parent)],
        )
        return

    if args.action == "export":
        print(export_contracts())
        return
    if not check_contracts():
        raise SystemExit(
            "Generated contracts are stale. Run: "
            "uv run --project apps/api replaytutor contracts export"
        )
    print("contracts are clean")
