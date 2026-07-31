from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "test-results"


@dataclass
class E2EStack:
    api_url: str
    web_url: str
    data_dir: Path
    restart_api: Callable[[], None]
    restart_web: Callable[[], None]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_url(url: str, processes: list[subprocess.Popen[str]], logs: list[Path]) -> None:
    deadline = time.monotonic() + 30
    last_error = "not attempted"
    while time.monotonic() < deadline:
        for process in processes:
            if process.poll() is not None:
                rendered_logs = "\n\n".join(
                    f"== {path.name} ==\n{path.read_text(encoding='utf-8', errors='replace')}"
                    for path in logs
                    if path.exists()
                )
                raise RuntimeError(
                    f"Test service exited with {process.returncode} while waiting for {url}\n"
                    f"{rendered_logs}"
                )
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, urllib.error.URLError) as error:
            last_error = str(error)
        time.sleep(0.1)
    rendered_logs = "\n\n".join(
        f"== {path.name} ==\n{path.read_text(encoding='utf-8', errors='replace')}"
        for path in logs
        if path.exists()
    )
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}\n{rendered_logs}")


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2)


def _write_codex_stub(bin_dir: Path, mode: Literal["fake", "unavailable"]) -> Path:
    executable = bin_dir / "codex"
    if mode == "unavailable":
        body = f"""#!{sys.executable}
import sys
print("codex unavailable in E2E", file=sys.stderr)
raise SystemExit(1)
"""
    else:
        body = f"""#!{sys.executable}
import json
import pathlib
import sys

if "--version" in sys.argv:
    print("codex-cli fake-e2e")
    raise SystemExit(0)

output = pathlib.Path(sys.argv[sys.argv.index("--output-last-message") + 1])
context = json.loads(pathlib.Path.cwd().joinpath("tutor_context.json").read_text())
bar = context["visible_bars"][-1]
bar_id = bar["bar_id"]
payload = {{
    "schema_version": "1.0",
    "summary": "E2E Tutor 已完成当前证据检查",
    "observations": [{{"text": "当前可见 K 线已核验。", "evidence_ids": [bar_id]}}],
    "inferences": [],
    "risks_and_unknowns": ["测试响应不构成交易建议。"],
    "rule_checks": [],
    "next_questions": ["失效条件是否足够明确？"],
    "annotations": [{{
        "shape": "marker",
        "label": "E2E Tutor 标注",
        "evidence_ids": [bar_id],
        "points": [{{"time": bar["close_time"], "price": bar["raw"]["close"]}}],
    }}],
    "disclaimer": "仅供训练复盘，不构成投资建议。",
}}
output.write_text(json.dumps(payload, ensure_ascii=False))
print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message"}}}}))
"""
    executable.write_text(body, encoding="utf-8")
    executable.chmod(0o755)
    return executable


@pytest.fixture
def e2e_stack_factory(
    tmp_path: Path,
) -> Generator[Callable[[Literal["fake", "unavailable"]], E2EStack], None, None]:
    processes: list[subprocess.Popen[str]] = []
    handles: list[object] = []
    stack_index = 0

    def start(mode: Literal["fake", "unavailable"] = "fake") -> E2EStack:
        nonlocal stack_index
        stack_index += 1
        stack_dir = tmp_path / f"stack-{stack_index}-{mode}"
        data_dir = stack_dir / "data"
        log_dir = stack_dir / "logs"
        bin_dir = stack_dir / "bin"
        codex_home = stack_dir / "codex-home"
        for path in (data_dir, log_dir, bin_dir, codex_home):
            path.mkdir(parents=True, exist_ok=True)
        _write_codex_stub(bin_dir, mode)
        (codex_home / "auth.json").write_text("{}", encoding="utf-8")

        api_port = _free_port()
        web_port = _free_port()
        api_url = f"http://127.0.0.1:{api_port}"
        web_url = f"http://127.0.0.1:{web_port}"
        api_env = os.environ.copy()
        api_env.update(
            {
                "CODEX_HOME": str(codex_home),
                "PATH": f"{bin_dir}{os.pathsep}{api_env['PATH']}",
                "REPLAYTUTOR_CORS_ORIGINS": web_url,
                "REPLAYTUTOR_DATA_DIR": str(data_dir),
            }
        )
        web_env = os.environ.copy()
        web_env["VITE_API_BASE_URL"] = api_url

        api_logs: list[Path] = []
        web_logs: list[Path] = []
        api_generation = 0
        web_generation = 0

        def spawn_api() -> subprocess.Popen[str]:
            nonlocal api_generation
            api_generation += 1
            api_log = log_dir / f"api-{api_generation}.log"
            api_logs.append(api_log)
            api_handle = api_log.open("w", encoding="utf-8")
            handles.append(api_handle)
            process = subprocess.Popen(
                [
                    str(ROOT / "scripts" / "uv"),
                    "run",
                    "--project",
                    "apps/api",
                    "uvicorn",
                    "replaytutor.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
                cwd=ROOT,
                env=api_env,
                stdout=api_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
            processes.append(process)
            return process

        def spawn_web() -> subprocess.Popen[str]:
            nonlocal web_generation
            web_generation += 1
            web_log = log_dir / f"web-{web_generation}.log"
            web_logs.append(web_log)
            web_handle = web_log.open("w", encoding="utf-8")
            handles.append(web_handle)
            process = subprocess.Popen(
                [
                    str(ROOT / "scripts" / "pnpm"),
                    "--filter",
                    "@replaytutor/web",
                    "exec",
                    "vite",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(web_port),
                    "--strictPort",
                ],
                cwd=ROOT,
                env=web_env,
                stdout=web_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
            processes.append(process)
            return process

        current = {"api": spawn_api(), "web": spawn_web()}
        _wait_for_url(
            f"{api_url}/api/v1/health",
            [current["api"], current["web"]],
            [*api_logs, *web_logs],
        )
        _wait_for_url(
            web_url,
            [current["api"], current["web"]],
            [*api_logs, *web_logs],
        )

        def restart_api() -> None:
            _stop_process(current["api"])
            current["api"] = spawn_api()
            _wait_for_url(
                f"{api_url}/api/v1/health",
                [current["api"], current["web"]],
                [*api_logs, *web_logs],
            )

        def restart_web() -> None:
            _stop_process(current["web"])
            current["web"] = spawn_web()
            _wait_for_url(
                web_url,
                [current["api"], current["web"]],
                [*api_logs, *web_logs],
            )

        return E2EStack(
            api_url=api_url,
            web_url=web_url,
            data_dir=data_dir,
            restart_api=restart_api,
            restart_web=restart_web,
        )

    yield start

    for process in reversed(processes):
        _stop_process(process)
    for handle in handles:
        handle.close()  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    with sync_playwright() as playwright:
        launched = playwright.chromium.launch(headless=True)
        yield launched
        launched.close()


@pytest.fixture
def page(
    browser: Browser,
    request: pytest.FixtureRequest,
) -> Generator[Page, None, None]:
    RESULTS_DIR.mkdir(exist_ok=True)
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    current_page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    current_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    current_page.on("pageerror", lambda error: page_errors.append(str(error)))
    yield current_page

    failed = bool(getattr(request.node, "rep_call", None) and request.node.rep_call.failed)
    release_acceptance = request.node.get_closest_marker("release_acceptance") is not None
    artifact_stem = request.node.nodeid.replace("/", "_").replace("::", "__")
    if failed or release_acceptance:
        prefix = "release-acceptance-" if release_acceptance else ""
        current_page.screenshot(
            path=RESULTS_DIR / f"{prefix}{artifact_stem}.png",
            full_page=True,
        )
        context.tracing.stop(path=RESULTS_DIR / f"{prefix}{artifact_stem}.zip")
    else:
        context.tracing.stop()
    context.close()
    assert console_errors == []
    assert page_errors == []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[object],
) -> Generator[None, object, None]:
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "release-acceptance-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "exit_status": exitstatus,
                "tests_collected": session.testscollected,
                "release_acceptance": exitstatus == 0,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
