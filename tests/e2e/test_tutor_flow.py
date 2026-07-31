from __future__ import annotations

import time
from uuid import uuid4

from playwright.sync_api import Page, expect

from .conftest import E2EStack
from .helpers import create_training_session


def test_tutor_response_uses_visible_evidence_and_separate_ai_layer(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]

    page.goto(f"{stack.web_url}/sessions/{session_id}")
    expect(page.get_by_text("codex-cli fake-e2e", exact=True)).to_be_visible(timeout=30_000)
    page.get_by_label("向 Codex 询问当前 frame").fill("核验当前可见证据")
    page.get_by_role("button", name="让 Codex 检查").click()
    expect(page.get_by_text("事实观察", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text("AI 图上标注", exact=True)).to_be_visible()
    expect(page.locator(".annotation-list", has_text="proposed")).to_be_visible()
    page.locator(".annotation-list button", has_text="E2E Tutor 标注").click()
    page.locator(".annotation-inspector").get_by_role("button", name="接受").click()
    expect(page.locator(".annotation-list", has_text="accepted")).to_be_visible()
    page.reload()
    expect(page.locator(".annotation-list", has_text="accepted")).to_be_visible()

    deadline = time.monotonic() + 10
    annotations = []
    while time.monotonic() < deadline:
        current = client.get(f"/api/v1/sessions/{session_id}").json()
        annotations = current["annotations"]
        if any(annotation["layer"] == "ai" for annotation in annotations):
            break
        time.sleep(0.1)
    ai_annotations = [annotation for annotation in annotations if annotation["layer"] == "ai"]
    assert len(ai_annotations) == 1
    assert ai_annotations[0]["provenance_run_id"]
    visible_at = created["session"]["frame"]["visible_at"]
    assert ai_annotations[0]["points"][0]["time"] <= visible_at
    client.close()


def test_codex_unavailable_does_not_block_deterministic_replay(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("unavailable")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]

    page.goto(f"{stack.web_url}/settings")
    expect(page.get_by_text("不可用", exact=True)).to_be_visible(timeout=30_000)
    page.goto(f"{stack.web_url}/sessions/{session_id}")
    expect(page.get_by_role("button", name="下一根 K 线")).to_be_enabled()
    expect(page.get_by_role("button", name="让 Codex 检查")).to_be_disabled()

    before = client.get(f"/api/v1/sessions/{session_id}").json()
    advanced = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "command_id": f"cmd_{uuid4()}",
            "expected_revision": before["session"]["revision"],
            "kind": "advance",
            "bars": 1,
        },
    )
    advanced.raise_for_status()
    assert advanced.json()["session"]["frame"]["current_index"] == (
        before["session"]["frame"]["current_index"] + 1
    )
    client.close()
