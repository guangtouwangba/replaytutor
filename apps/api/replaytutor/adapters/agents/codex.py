from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from replaytutor.contracts import AgentCapability, TutorResponse


class CodexAdapterError(RuntimeError):
    pass


class CodexAdapter:
    agent_id = "codex-local"

    def discover(self) -> AgentCapability:
        executable = shutil.which("codex")
        if executable is None:
            return AgentCapability(
                installed=False,
                available=False,
                authentication="unknown",
                diagnostics=["Codex CLI is not installed or not on PATH."],
            )
        try:
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            return AgentCapability(
                installed=True,
                executable=executable,
                available=False,
                authentication="unknown",
                diagnostics=[f"Version probe failed: {error}"],
            )
        return AgentCapability(
            installed=True,
            executable=executable,
            version=version,
            available=True,
            authentication="unknown",
            diagnostics=[
                "Authentication is verified by the first structured self-check.",
                "MVP uses a read-only sandbox and ephemeral state.",
                "User config and project rules are ignored.",
            ],
        )

    def run(
        self,
        workspace: Path,
        *,
        timeout_seconds: int,
        on_process: Callable[[subprocess.Popen[str]], None],
    ) -> TutorResponse:
        capability = self.discover()
        if not capability.available or capability.executable is None:
            raise CodexAdapterError("Codex CLI is unavailable")
        result_path = workspace / "result.json"
        command = [
            capability.executable,
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
            "--output-schema",
            str(workspace / "tutor_response.schema.json"),
            "--output-last-message",
            str(result_path),
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--cd",
            str(workspace),
            "-",
        ]
        environment = {
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "PATH",
                "HOME",
                "CODEX_HOME",
                "SSL_CERT_FILE",
                "SSL_CERT_DIR",
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "NO_PROXY",
            }
        }
        original_codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).expanduser()
        auth_path = original_codex_home / "auth.json"
        if not auth_path.is_file():
            raise CodexAdapterError("Codex authentication is unavailable; run `codex login` first")
        prompt = (
            "Follow TUTOR_INSTRUCTIONS.md. Read tutor_context.json only. "
            "Do not run tools or inspect any other path. Return one response "
            "matching tutor_response.schema.json."
        )
        with tempfile.TemporaryDirectory(prefix="replaytutor-codex-home-") as isolated_home:
            Path(isolated_home, "auth.json").symlink_to(auth_path)
            environment["CODEX_HOME"] = isolated_home
            process = subprocess.Popen(
                command,
                cwd=workspace,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            on_process(process)
            try:
                stdout, stderr = process.communicate(
                    prompt,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as error:
                process.kill()
                process.communicate()
                raise TimeoutError("Codex Tutor timed out") from error
        (workspace / "events.jsonl").write_text(stdout, encoding="utf-8")
        (workspace / "stderr.log").write_text(stderr, encoding="utf-8")
        if process.returncode != 0:
            diagnostic = (
                stderr.strip().splitlines()[-1] if stderr.strip() else self._event_error(stdout)
            )
            raise CodexAdapterError(f"Codex exited with code {process.returncode}: {diagnostic}")
        if not result_path.is_file():
            raise CodexAdapterError("Codex completed without result.json")
        try:
            return TutorResponse.model_validate_json(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CodexAdapterError(f"Codex returned invalid structured output: {error}") from error

    @staticmethod
    def _event_error(stdout: str) -> str:
        for line in reversed(stdout.splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "error":
                return str(event.get("message", "unknown error"))
            error = event.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])
        return "unknown error"
