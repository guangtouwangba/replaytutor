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

    page.get_by_role("button", name="继续追问").click()
    page.get_by_label("向 Codex 询问当前 frame").fill("给出第二条可修订建议")
    page.get_by_role("button", name="让 Codex 检查").click()
    expect(page.get_by_text("AI 图上标注", exact=True)).to_be_visible(timeout=30_000)
    page.get_by_role("button", name="继续追问").click()
    page.get_by_label("向 Codex 询问当前 frame").fill("给出第三条可拒绝建议")
    page.get_by_role("button", name="让 Codex 检查").click()
    expect(page.get_by_text("AI 图上标注", exact=True)).to_be_visible(timeout=30_000)

    ai_rows = page.locator(".annotation-list button", has_text="E2E Tutor 标注")
    expect(ai_rows).to_have_count(3)
    ai_rows.nth(0).click()
    page.locator(".annotation-inspector").get_by_role("button", name="接受").click()
    expect(page.locator(".annotation-list", has_text="accepted")).to_be_visible()

    page.locator(".annotation-list button", has_text="proposed").first.click()
    page.locator(".annotation-inspector").get_by_role("button", name="拒绝").click()
    expect(page.locator(".annotation-list", has_text="rejected")).to_be_visible()

    page.locator(".annotation-list button", has_text="proposed").first.click()
    page.locator(".annotation-inspector input").first.fill("E2E 用户修订 AI 标注")
    page.get_by_role("button", name="保存修改").click()
    expect(page.locator(".annotation-list", has_text="E2E 用户修订 AI 标注")).to_be_visible()

    page.reload()
    expect(page.locator(".annotation-list", has_text="accepted")).to_be_visible()
    expect(page.locator(".annotation-list", has_text="E2E 用户修订 AI 标注")).to_be_visible()
    expect(page.locator(".annotation-list", has_text="rejected")).to_be_visible()

    deadline = time.monotonic() + 10
    dispositions = []
    while time.monotonic() < deadline:
        dispositions = client.get(
            f"/api/v1/sessions/{session_id}/annotations/dispositions"
        ).json()["dispositions"]
        if len(dispositions) == 3:
            break
        time.sleep(0.1)
    states = [item["state"] for item in dispositions]
    assert states.count("accepted") == 2
    assert states.count("rejected") == 1
    revised = next(
        item for item in dispositions if item["effective_label"] == "E2E 用户修订 AI 标注"
    )
    assert revised["original_annotation"]["label"] == "E2E Tutor 标注"
    assert all(
        item["original_annotation"]["layer"] == "ai"
        and item["original_annotation"]["provenance_run_id"]
        for item in dispositions
    )
    visible_at = created["session"]["frame"]["visible_at"]
    assert all(
        item["original_annotation"]["points"][0]["time"] <= visible_at
        for item in dispositions
    )
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

    locked = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": f"cmd_{uuid4()}",
            "expected_revision": 1,
            "side": "BUY",
            "thesis": "Agent 不可用时仍按确定性计划执行",
            "invalidation": "结构失效退出",
            "risk_amount": "100",
        },
    )
    locked.raise_for_status()
    order = client.post(
        f"/api/v1/sessions/{session_id}/orders",
        json={
            "command_id": f"cmd_{uuid4()}",
            "expected_revision": 1,
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.01",
        },
    )
    order.raise_for_status()
    filled = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "command_id": f"cmd_{uuid4()}",
            "expected_revision": 1,
            "kind": "advance",
            "bars": 1,
        },
    )
    filled.raise_for_status()
    assert filled.json()["execution"]["fills"]
    finished = client.post(
        f"/api/v1/sessions/{session_id}/finish",
        json={
            "command_id": f"cmd_{uuid4()}",
            "expected_revision": 2,
        },
    )
    finished.raise_for_status()
    review = client.get(f"/api/v1/sessions/{session_id}/review")
    review.raise_for_status()
    assert review.json()["review_hash"]
    page.goto(f"{stack.web_url}/sessions/{session_id}/review")
    expect(page.get_by_role("heading", name="确定性训练复盘")).to_be_visible()
    client.close()
