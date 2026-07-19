from __future__ import annotations

import json
from pathlib import Path

from replaytutor.contracts import ErrorEnvelope, HealthResponse


def contract_path() -> Path:
    return (
        Path(__file__).resolve().parents[3] / "packages" / "contracts" / "schema" / "contracts.json"
    )


def render_contracts() -> str:
    schemas = {
        "schema_version": "1.0",
        "models": {
            "ErrorEnvelope": ErrorEnvelope.model_json_schema(),
            "HealthResponse": HealthResponse.model_json_schema(),
        },
    }
    return json.dumps(schemas, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_contracts() -> Path:
    path = contract_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_contracts(), encoding="utf-8")
    return path


def check_contracts() -> bool:
    path = contract_path()
    return path.is_file() and path.read_text(encoding="utf-8") == render_contracts()
