from __future__ import annotations

from datetime import datetime
import time

from playwright.sync_api import Page, expect

from .conftest import E2EStack
from .helpers import command_id


def test_user_can_complete_core_training_flow(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")

    page.goto(f"{stack.web_url}/data")
    expect(page.get_by_role("heading", name="数据中心")).to_be_visible()
    page.get_by_role("button", name="载入真实 BTC 样例").click()
    expect(page.get_by_text("44,640", exact=True).first).to_be_visible(timeout=30_000)

    page.goto(f"{stack.web_url}/setup")
    page.get_by_role("button", name="创建训练会话").click()
    expect(page.get_by_role("heading", name="先锁定交易计划")).to_be_visible(timeout=30_000)
    session_id = page.url.rstrip("/").split("/")[-1]

    page.get_by_label("交易逻辑").fill("顺势突破并等待下一根确认")
    page.get_by_label("失效条件").fill("价格跌破当前结构低点")
    page.get_by_role("button", name="锁定计划").click()
    expect(page.get_by_role("heading", name="提交模拟订单")).to_be_visible()

    page.get_by_role("button", name="提交 · 下一根激活").click()
    expect(page.get_by_text("PENDING", exact=True)).to_be_visible()

    page.get_by_role("button", name="下一根 K 线").click()
    expect(page.get_by_text("FILLED", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("FILLED", exact=True)).to_be_visible()

    page.get_by_label("标注文字").fill("E2E 用户观察")
    page.get_by_role("button", name="标记当前价格").click()
    deadline = time.monotonic() + 10
    annotations = []
    while time.monotonic() < deadline:
        annotation_response = page.request.get(
            f"{stack.api_url}/api/v1/sessions/{session_id}"
        )
        annotations = annotation_response.json()["annotations"]
        if any(annotation["label"] == "E2E 用户观察" for annotation in annotations):
            break
        time.sleep(0.1)
    assert any(annotation["label"] == "E2E 用户观察" for annotation in annotations)

    with page.expect_response(
        lambda response: response.url.endswith(f"/api/v1/sessions/{session_id}/finish")
        and response.ok
    ):
        page.get_by_role("button", name="结束会话").click()
    expect(page).to_have_url(f"{stack.web_url}/sessions/{session_id}/complete")
    expect(page.get_by_text("确定性复盘", exact=False)).to_be_visible(timeout=30_000)

    response = page.request.get(f"{stack.api_url}/api/v1/sessions/{session_id}")
    assert response.ok
    session = response.json()
    visible_at = datetime.fromisoformat(session["session"]["frame"]["visible_at"])
    assert session["session"]["status"] == "completed"
    assert session["execution"]["fills"]
    assert all(datetime.fromisoformat(bar["close_time"]) <= visible_at for bar in session["bars"])


def test_order_is_not_filled_before_activation_bar(page: Page, e2e_stack_factory) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    response = page.request.post(f"{stack.api_url}/api/v1/datasets/golden", data={})
    assert response.ok
    snapshot_id = response.json()["snapshot_id"]
    response = page.request.post(
        f"{stack.api_url}/api/v1/sessions",
        data={
            "snapshot_id": snapshot_id,
            "start_mode": "beginning",
            "seed": 7,
            "warmup_bars": 120,
            "initial_cash": "100000",
            "hidden_real_date": True,
            "playbook_id": None,
        },
    )
    session = response.json()
    session_id = session["session"]["session_id"]
    revision = session["session"]["revision"]
    plan_response = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{session_id}/plan",
        data={
            "command_id": command_id(),
            "expected_revision": revision,
            "side": "BUY",
            "thesis": "等待下一根确认",
            "invalidation": "跌破结构低点",
            "risk_amount": "100",
        },
    )
    assert plan_response.ok, plan_response.text()
    plan = plan_response.json()
    placed_response = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{session_id}/orders",
        data={
            "command_id": command_id(),
            "expected_revision": plan["session"]["revision"],
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.01",
        },
    )
    assert placed_response.ok, placed_response.text()
    placed = placed_response.json()
    assert placed["order"]["status"] == "PENDING"
    assert placed["execution"]["fills"] == []
