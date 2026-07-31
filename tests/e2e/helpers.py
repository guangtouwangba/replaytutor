from __future__ import annotations

from uuid import uuid4

import httpx


def post(client: httpx.Client, path: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def command_id() -> str:
    return f"cmd_{uuid4()}"


def create_training_session(api_url: str) -> tuple[httpx.Client, dict[str, object]]:
    client = httpx.Client(base_url=api_url, timeout=30)
    snapshot = post(client, "/api/v1/datasets/golden", {})
    session = post(
        client,
        "/api/v1/sessions",
        {
            "snapshot_id": snapshot["snapshot_id"],
            "start_mode": "beginning",
            "seed": 7,
            "warmup_bars": 120,
            "initial_cash": "100000",
            "hidden_real_date": True,
            "playbook_id": None,
        },
    )
    return client, session
