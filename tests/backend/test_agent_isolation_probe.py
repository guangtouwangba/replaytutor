from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_probe_dry_run_keeps_host_read_only_disabled() -> None:
    project_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "agent-isolation-probe.py")],
        check=True,
        capture_output=True,
        text=True,
    )
    results = json.loads(completed.stdout)

    host_results = [result for result in results if result["mode"] == "host_read_only"]
    assert {result["agent"] for result in host_results} == {"codex", "claude"}
    assert all(result["status"] == "disabled" for result in host_results)


def test_probe_commands_disable_persistence_and_never_bypass_sandbox() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "scripts" / "agent-isolation-probe.py"
    ).read_text()

    assert "--ephemeral" in source
    assert "--no-session-persistence" in source
    assert "--sandbox" in source and '"read-only"' in source
    assert "dangerously-bypass" not in source
    assert "dangerously-skip-permissions" not in source
