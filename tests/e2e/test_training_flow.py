from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, expect

from .conftest import E2EStack
from .helpers import command_id, create_training_session


def test_home_supports_english_locale_and_lazy_demo(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    page.add_init_script(
        "localStorage.setItem('replaytutor:locale', 'en-US'); "
        "localStorage.setItem('replaytutor:locale-preference', 'en-US'); "
        "localStorage.setItem('replaytutor:onboarding-complete', '1');"
    )
    page.goto(stack.web_url)
    expect(
        page.get_by_role(
            "heading",
            name="Train the decision with only what was visible then.",
        )
    ).to_be_visible()
    poster = page.get_by_role("button", name="Play ReplayTutor demo")
    expect(poster).to_be_visible()
    expect(page.locator(".demo-media video")).to_have_count(0)
    poster.click()
    expect(page.locator(".demo-media video")).to_be_visible()


def test_workbench_shortcuts_and_order_draft_support_english_locale(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]
    page.add_init_script(
        "localStorage.setItem('replaytutor:locale', 'en-US'); "
        "localStorage.setItem('replaytutor:locale-preference', 'en-US');"
    )
    page.goto(f"{stack.web_url}/sessions/{session_id}")
    expect(page.get_by_role("heading", name="Lock the trading plan first")).to_be_visible()

    page.keyboard.press("?")
    expect(
        page.get_by_role("dialog", name="ReplayTutor keyboard shortcuts")
    ).to_be_visible()
    expect(page.get_by_text("Replay safety boundary")).to_be_visible()
    expect(page.get_by_text("Paper-order drafts")).to_be_visible()
    page.keyboard.press("Escape")

    page.keyboard.press("Control+K")
    expect(page.get_by_role("dialog", name="Search commands and tools")).to_be_visible()
    expect(page.get_by_placeholder("Search tools, timeframes, or actions…")).to_be_visible()
    page.keyboard.press("Escape")

    page.get_by_label("Trade thesis").fill("Breakout continuation after confirmation")
    page.get_by_label("Invalidation").fill("Price loses the visible structure low")
    page.get_by_role("button", name="Lock plan").click()
    expect(page.get_by_role("heading", name="Submit paper order")).to_be_visible()
    expect(page.get_by_label("Order type")).to_be_visible()
    expect(page.get_by_role("button", name="Submit · activates on next bar")).to_be_visible()
    client.close()


def test_restored_sell_plan_keeps_order_request_on_sell_side(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]
    plan = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": command_id(),
            "expected_revision": 0,
            "side": "SELL",
            "thesis": "Visible structure has failed and the plan is to sell",
            "invalidation": "Price closes back above the visible structure high",
            "risk_amount": "100",
        },
    )
    plan.raise_for_status()

    page.add_init_script(
        "localStorage.setItem('replaytutor:locale', 'en-US'); "
        "localStorage.setItem('replaytutor:locale-preference', 'en-US');"
    )
    page.goto(f"{stack.web_url}/sessions/{session_id}")
    expect(page.get_by_role("heading", name="Submit paper order")).to_be_visible()

    submitted: list[dict[str, object]] = []

    def capture_order(route: Route) -> None:
        payload = route.request.post_data_json
        assert isinstance(payload, dict)
        submitted.append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session": plan.json()["session"],
                    "execution": plan.json()["execution"],
                }
            ),
        )

    page.route(f"**/api/v1/sessions/{session_id}/orders", capture_order)
    page.get_by_role("button", name="Submit · activates on next bar").click()
    expect(page.get_by_role("button", name="Submit · activates on next bar")).to_be_enabled()
    assert submitted[0]["side"] == "SELL"
    client.close()


def test_user_can_complete_core_training_flow(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")

    health = page.request.get(f"{stack.api_url}/api/v1/health")
    assert health.ok
    assert (
        health.json()["database"]["migration_current"]
        == health.json()["database"]["migration_head"]
        == "0019_tutor_threads"
    )

    page.goto(f"{stack.web_url}/data")
    expect(page.get_by_role("heading", name="数据中心")).to_be_visible()
    page.get_by_role("button", name="载入真实 BTC 样例").click()
    expect(page.get_by_text("44,640", exact=True).first).to_be_visible(timeout=30_000)

    page.goto(f"{stack.web_url}/setup")
    page.get_by_role("button", name="现货", exact=True).click()
    snapshot_group = page.get_by_role("radiogroup", name="选择数据集 Snapshot")
    expect(snapshot_group).to_be_visible()
    expect(page.get_by_text("后续配置尚未展开")).to_be_visible()
    snapshot_group.get_by_role("radio").first.click()
    expect(page.get_by_text("已选择本地数据", exact=True)).to_be_visible()
    page.get_by_role("button", name="使用所选数据开始").click()
    expect(page.get_by_role("heading", name="先锁定交易计划")).to_be_visible(
        timeout=30_000
    )
    session_id = page.url.rstrip("/").split("/")[-1]

    page.get_by_role("button", name="交易", exact=True).click()
    expect(page.locator(".workbench-grid")).to_have_class(
        re.compile(r"right-tool-collapsed")
    )
    expect(page.get_by_role("button", name="交易", exact=True)).to_have_attribute(
        "aria-pressed", "false"
    )
    page.reload()
    expect(page.locator(".workbench-grid")).to_have_class(
        re.compile(r"right-tool-collapsed")
    )
    page.get_by_role("button", name="交易", exact=True).click()
    expect(page.get_by_role("button", name="收起交易决策台")).to_be_visible()

    page.get_by_role("tab", name="市场深度").click()
    expect(page.get_by_text("该时刻没有历史 L2 盘口")).to_be_visible()
    expect(page.get_by_text("不会用今天的实时盘口冒充历史盘口", exact=False)).to_be_visible()
    page.get_by_role("tab", name="订单").click()
    expect(page.get_by_role("heading", name="先锁定交易计划")).to_be_visible()

    with page.expect_response(
        lambda response: "timeframe=4h" in response.url and response.ok
    ):
        page.get_by_role("button", name="4h", exact=True).click()
    expect(page.get_by_role("button", name="4h", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.get_by_label("BTCUSDT 4h 回放 K 线图")).to_be_visible()

    page.get_by_label("交易逻辑").fill("顺势突破并等待下一根确认")
    page.get_by_label("失效条件").fill("价格跌破当前结构低点")
    page.get_by_role("button", name="锁定计划").click()
    expect(page.get_by_role("heading", name="提交模拟订单")).to_be_visible()

    page.get_by_role("button", name="提交 · 下一根激活").click()
    expect(page.get_by_text("PENDING", exact=True)).to_be_visible()
    expect(page.locator(".rule-checklist")).to_contain_text("risk amount within limit")
    expect(page.locator(".rule-checklist .rule-status.passed")).to_have_count(4)
    expect(page.locator(".rule-checklist .rule-status.failed")).to_have_count(1)
    expect(page.locator(".rule-checklist .rule-status.unknown")).to_have_count(1)

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

    page.get_by_role("button", name="Chat", exact=True).click()
    page.get_by_label("发送给 Codex Tutor").fill("为复盘生成独立 AI 证据")
    page.get_by_role("button", name="发送", exact=True).click()
    expect(page.get_by_text("AI 图上标注", exact=True)).to_be_visible(timeout=30_000)
    page.get_by_role("button", name="交易", exact=True).click()
    expect(page.locator(".annotation-list", has_text="E2E Tutor 标注")).to_be_visible()

    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/v1/sessions/{session_id}/finish")
            and response.ok
        )
    ):
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="结束会话").click()
    expect(page).to_have_url(f"{stack.web_url}/sessions/{session_id}/complete")
    expect(page.get_by_text("确定性复盘", exact=False)).to_be_visible(timeout=30_000)
    expect(page.locator(".review-rule-checks")).to_contain_text("evaluator 1.0")
    expect(page.locator(".review-rule-checks .rule-status.passed")).to_have_count(5)
    expect(page.locator(".review-rule-checks .rule-status.failed")).to_have_count(1)
    expect(page.get_by_role("img", name="会话净值曲线")).to_be_visible()
    expect(page.locator(".review-timeline-panel")).to_contain_text("训练会话结束")
    page.get_by_role("link", name="打开完整复盘").click()
    review_url = page.url
    evidence_kinds = ["plan", "order", "fill", "user_annotation", "ai_annotation"]
    assert {
        item.locator("span").inner_text()
        for item in page.locator(".evidence-row").all()
    } >= set(evidence_kinds)
    for kind in evidence_kinds:
        evidence_link = page.locator(".evidence-row", has_text=kind).first
        evidence_dom_id = evidence_link.get_attribute("id")
        evidence_href = evidence_link.get_attribute("href")
        assert evidence_dom_id is not None
        assert evidence_href is not None
        evidence_link.click()
        expect(page).to_have_url(f"{stack.web_url}{evidence_href}")
        expect(page.get_by_role("button", name="下一根 K 线")).to_be_disabled()
        expect(page.locator(".evidence-focus-card")).to_contain_text(kind)
        expect(page.locator(".replay-chart-shell")).to_have_attribute(
            "data-evidence-id",
            evidence_dom_id.removeprefix("evidence-"),
        )
        if kind == "plan":
            expect(page.locator(".evidence-focus-card")).to_contain_text(
                "该证据没有价格坐标"
            )
        page.goto(review_url)
        expect(page.locator(".evidence-row").first).to_be_visible()

    evidence_link = page.locator(".evidence-row").first
    evidence_dom_id = evidence_link.get_attribute("id")
    evidence_href = evidence_link.get_attribute("href")
    assert evidence_dom_id is not None
    assert evidence_href is not None
    evidence_link.click()
    expect(page).to_have_url(f"{stack.web_url}{evidence_href}")
    expect(page.get_by_role("button", name="下一根 K 线")).to_be_disabled()
    expect(page.locator(".evidence-focus-card")).to_be_visible()
    expect(page.locator(".replay-chart-shell")).to_have_attribute(
        "data-evidence-id",
        evidence_dom_id.removeprefix("evidence-"),
    )
    page.reload()
    expect(page.locator(".evidence-focus-card")).to_be_visible()
    page.get_by_role("link", name="返回证据索引").click()
    expect(page).to_have_url(
        f"{stack.web_url}/sessions/{session_id}/review#{evidence_dom_id}"
    )
    expect(page.locator(f'[id="{evidence_dom_id}"]')).to_be_focused()

    response = page.request.get(f"{stack.api_url}/api/v1/sessions/{session_id}")
    assert response.ok
    session = response.json()
    visible_at = datetime.fromisoformat(session["session"]["frame"]["visible_at"])
    assert session["session"]["status"] == "completed"
    assert session["execution"]["fills"]
    assert all(
        datetime.fromisoformat(bar["close_time"]) <= visible_at
        for bar in session["bars"]
    )

    page.goto(f"{stack.web_url}/sessions")
    page.get_by_label(f"移入回收站 {session_id}").click()
    expect(page.locator(".session-trash")).to_contain_text(session_id[:16])
    page.locator(".session-trash").get_by_role("button", name="恢复").click()
    expect(page.get_by_label(f"移入回收站 {session_id}")).to_be_visible()


def test_order_is_not_filled_before_activation_bar(
    page: Page, e2e_stack_factory
) -> None:
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


def test_market_limit_and_bracket_orders_respect_activation_boundaries(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")

    def session_with_plan(thesis: str) -> tuple[dict, str]:
        response = page.request.post(
            f"{stack.api_url}/api/v1/datasets/golden",
            data={},
        )
        assert response.ok
        created = page.request.post(
            f"{stack.api_url}/api/v1/sessions",
            data={
                "snapshot_id": response.json()["snapshot_id"],
                "start_mode": "beginning",
                "seed": 7,
                "warmup_bars": 20,
                "initial_cash": "100000",
                "hidden_real_date": True,
                "playbook_id": None,
            },
        ).json()
        session_id = created["session"]["session_id"]
        locked = page.request.post(
            f"{stack.api_url}/api/v1/sessions/{session_id}/plan",
            data={
                "command_id": command_id(),
                "expected_revision": 0,
                "side": "BUY",
                "thesis": thesis,
                "invalidation": "结构失效时退出",
                "risk_amount": "100",
            },
        )
        assert locked.ok, locked.text()
        return created, session_id

    market_created, market_session_id = session_with_plan("市价下一根确认")
    market = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{market_session_id}/orders",
        data={
            "command_id": command_id(),
            "expected_revision": 0,
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.01",
        },
    ).json()
    assert market["order"]["status"] == "PENDING"
    assert market["order"]["activate_index"] == (
        market_created["session"]["frame"]["current_index"] + 1
    )

    _, limit_session_id = session_with_plan("限价等待回调")
    limit = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{limit_session_id}/orders",
        data={
            "command_id": command_id(),
            "expected_revision": 0,
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": "0.01",
            "limit_price": "1.00",
        },
    ).json()
    assert limit["order"]["status"] == "PENDING"
    limit_advanced = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{limit_session_id}/commands",
        data={
            "command_id": command_id(),
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    ).json()
    assert limit_advanced["execution"]["orders"][0]["status"] == "PENDING"
    assert limit_advanced["execution"]["fills"] == []

    bracket_created, bracket_session_id = session_with_plan("括号单保护退出")
    bracket = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{bracket_session_id}/orders",
        data={
            "command_id": command_id(),
            "expected_revision": 0,
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.01",
            "take_profit_price": "1.00",
            "protective_stop_price": "1.00",
        },
    ).json()
    orders = bracket["execution"]["orders"]
    parent = next(order for order in orders if order["parent_order_id"] is None)
    children = [
        order for order in orders if order["parent_order_id"] == parent["order_id"]
    ]
    assert parent["status"] == "PENDING"
    assert all(
        child["activate_index"] == bracket_created["session"]["frame"]["total_bars"]
        for child in children
    )
    after_parent = page.request.post(
        f"{stack.api_url}/api/v1/sessions/{bracket_session_id}/commands",
        data={
            "command_id": command_id(),
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    ).json()
    assert len(after_parent["execution"]["fills"]) == 1
    assert all(
        child["status"] == "PENDING"
        and child["activate_index"]
        == bracket_created["session"]["frame"]["current_index"] + 2
        for child in after_parent["execution"]["orders"]
        if child["parent_order_id"] is not None
    )


@pytest.mark.allow_console_errors(r"Failed to load resource: net::ERR_CONNECTION_REFUSED")
def test_api_and_web_restart_preserve_session_ledger_annotations_and_review(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]
    locked = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": command_id(),
            "expected_revision": 0,
            "side": "BUY",
            "thesis": "重启前锁定确定性计划",
            "invalidation": "结构失效退出",
            "risk_amount": "100",
        },
    )
    locked.raise_for_status()
    order = client.post(
        f"/api/v1/sessions/{session_id}/orders",
        json={
            "command_id": command_id(),
            "expected_revision": 0,
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.01",
        },
    )
    order.raise_for_status()
    advanced = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "command_id": command_id(),
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    )
    advanced.raise_for_status()
    advanced_body = advanced.json()
    visible = advanced_body["bars"][-1]
    annotation = client.post(
        f"/api/v1/sessions/{session_id}/annotations",
        json={
            "command_id": command_id(),
            "expected_revision": 1,
            "shape": "marker",
            "label": "重启持久化标注",
            "points": [
                {
                    "time": visible["close_time"],
                    "price": visible["raw"]["close"],
                }
            ],
        },
    )
    annotation.raise_for_status()
    finished = client.post(
        f"/api/v1/sessions/{session_id}/finish",
        json={"command_id": command_id(), "expected_revision": 1},
    )
    finished.raise_for_status()
    before = client.get(f"/api/v1/sessions/{session_id}").json()
    review_before = client.get(f"/api/v1/sessions/{session_id}/review").json()
    database_path = stack.data_dir / "app.db"
    with sqlite3.connect(database_path) as connection:
        ledger_before = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0) "
            "FROM ledger_journal"
        ).fetchone()

    stack.restart_api()
    stack.restart_web()

    after = client.get(f"/api/v1/sessions/{session_id}").json()
    review_after = client.get(f"/api/v1/sessions/{session_id}/review").json()
    with sqlite3.connect(database_path) as connection:
        ledger_after = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0) "
            "FROM ledger_journal"
        ).fetchone()
    assert after["session"]["revision"] == before["session"]["revision"]
    assert after["execution"] == before["execution"]
    assert after["annotations"] == before["annotations"]
    assert review_after["review_hash"] == review_before["review_hash"]
    assert ledger_after == ledger_before
    assert ledger_after is not None
    assert ledger_after[0] > 0
    assert ledger_after[1] == ledger_after[2]

    page.goto(f"{stack.web_url}/sessions/{session_id}/review")
    expect(page.get_by_role("heading", name="确定性训练复盘")).to_be_visible()
    expect(page.locator(".evidence-row", has_text="重启持久化标注")).to_be_visible()
    client.close()


def test_drawings_and_dispositions_survive_reload(
    page: Page, e2e_stack_factory
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]
    page.goto(f"{stack.web_url}/sessions/{session_id}")
    expect(page.get_by_role("button", name="下一根 K 线")).to_be_visible()

    page.get_by_role("button", name="线类工具").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^趋势线")).click()
    page.get_by_label("标注文字").first.fill("E2E 趋势线")
    chart = page.locator(".replay-chart")
    box = chart.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.45)
    expect(chart).to_have_attribute("data-preview-active", "true")
    page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.35)
    page.mouse.click(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.35)
    expect(chart).to_have_attribute("data-preview-active", "false")
    expect(page.locator(".annotation-list", has_text="E2E 趋势线")).to_be_visible(
        timeout=15_000
    )

    page.locator(".annotation-list button", has_text="E2E 趋势线").click()
    page.locator(".annotation-inspector input").first.fill("E2E 修订趋势线")
    page.get_by_role("button", name="保存修改").click()
    expect(page.locator(".annotation-list", has_text="E2E 修订趋势线")).to_be_visible()
    page.reload()
    expect(page.locator(".annotation-list", has_text="E2E 修订趋势线")).to_be_visible()

    page.locator(".annotation-list button", has_text="E2E 修订趋势线").click()
    page.locator(".annotation-inspector").get_by_role("button", name="删除").click()
    expect(page.locator(".annotation-list", has_text="deleted")).to_be_visible()

    page.get_by_role("button", name="图形形态").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^价格区域")).click()
    page.get_by_label("标注文字").first.fill("E2E 矩形")
    page.mouse.click(box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.4)
    page.mouse.click(box["x"] + box["width"] * 0.62, box["y"] + box["height"] * 0.62)
    expect(page.locator(".annotation-list", has_text="E2E 矩形")).to_be_visible()
    rectangle_dispositions = client.get(
        f"/api/v1/sessions/{session_id}/annotations/dispositions"
    ).json()["dispositions"]
    assert any(
        item["original_annotation"]["shape"] == "zone"
        for item in rectangle_dispositions
    )
    page.locator(".annotation-list button", has_text="E2E 矩形").click()
    page.locator(".annotation-inspector input").first.fill("E2E 修订矩形")
    page.get_by_role("button", name="保存修改").click()
    expect(page.locator(".annotation-list", has_text="E2E 修订矩形")).to_be_visible()
    page.locator(".annotation-list button", has_text="E2E 修订矩形").click()
    page.locator(".annotation-inspector").get_by_role("button", name="删除").click()
    expect(page.locator(".annotation-list button", has_text="deleted")).to_have_count(2)

    page.get_by_label("标注文字").first.fill("E2E 标记")
    page.get_by_role("button", name="标记当前价格").click()
    expect(page.locator(".annotation-list", has_text="E2E 标记")).to_be_visible()
    page.locator(".annotation-list button", has_text="E2E 标记").click()
    page.locator(".annotation-inspector input").first.fill("E2E 修订标记")
    page.get_by_role("button", name="保存修改").click()
    expect(page.locator(".annotation-list", has_text="E2E 修订标记")).to_be_visible()
    page.locator(".annotation-list button", has_text="E2E 修订标记").click()
    page.locator(".annotation-inspector").get_by_role("button", name="删除").click()
    expect(page.locator(".annotation-list button", has_text="deleted")).to_have_count(3)
    page.reload()
    expect(page.locator(".annotation-list button", has_text="deleted")).to_have_count(3)

    before_count = len(
        client.get(f"/api/v1/sessions/{session_id}/annotations/dispositions").json()[
            "dispositions"
        ]
    )
    page.get_by_role("button", name="图形形态").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^价格区域")).click()
    page.mouse.click(box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.5)
    page.keyboard.press("Escape")
    page.wait_for_timeout(250)
    after_count = len(
        client.get(f"/api/v1/sessions/{session_id}/annotations/dispositions").json()[
            "dispositions"
        ]
    )
    assert after_count == before_count

    box = chart.bounding_box()
    assert box is not None
    page.get_by_role("button", name="关闭磁吸").click()
    page.get_by_role("button", name="预测与测量").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^多头仓位计划")).click()
    page.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.45)
    page.mouse.click(box["x"] + box["width"] * 0.42, box["y"] + box["height"] * 0.55)
    page.mouse.click(box["x"] + box["width"] * 0.56, box["y"] + box["height"] * 0.3)
    expect(page.locator(".annotation-list", has_text="多头仓位计划 · R:R")).to_be_visible()

    page.get_by_role("button", name="预测与测量").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^空头仓位计划")).click()
    page.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.5)
    page.mouse.click(box["x"] + box["width"] * 0.42, box["y"] + box["height"] * 0.32)
    page.mouse.click(box["x"] + box["width"] * 0.56, box["y"] + box["height"] * 0.7)
    expect(page.locator(".annotation-list", has_text="空头仓位计划 · R:R")).to_be_visible()

    position_plans = [
        item["original_annotation"]
        for item in client.get(
            f"/api/v1/sessions/{session_id}/annotations/dispositions"
        ).json()["dispositions"]
        if item["original_annotation"]["tool"]
        in {"long_position", "short_position", "risk_reward"}
    ]
    assert {item["metadata"]["side"] for item in position_plans} == {"long", "short"}
    assert all(float(item["metadata"]["risk_reward_ratio"]) > 0 for item in position_plans)

    page.get_by_role("button", name="预测与测量").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^日期与价格测量")).click()
    page.mouse.click(box["x"] + box["width"] * 0.32, box["y"] + box["height"] * 0.62)
    page.mouse.click(box["x"] + box["width"] * 0.52, box["y"] + box["height"] * 0.38)
    expect(page.locator(".annotation-list", has_text="测量 +")).to_be_visible()
    page.get_by_role("button", name="撤销上一次图表对象操作").click()
    expect(page.locator(".annotation-list button", has_text="deleted")).to_have_count(4)
    page.get_by_role("button", name="重做上一次图表对象操作").click()
    expect(page.locator(".annotation-list", has_text="测量 +")).to_be_visible()
    page.get_by_role("button", name="线类工具").click()
    page.get_by_role("menuitemradio", name=re.compile(r"^平行通道")).click()
    page.mouse.click(box["x"] + box["width"] * 0.28, box["y"] + box["height"] * 0.62)
    page.mouse.click(box["x"] + box["width"] * 0.48, box["y"] + box["height"] * 0.42)
    page.mouse.click(box["x"] + box["width"] * 0.38, box["y"] + box["height"] * 0.3)
    expect(page.locator(".annotation-list", has_text="平行通道")).to_be_visible()

    page.get_by_role("button", name="斐波那契工具").click()
    fib_tool = page.get_by_role("menuitemradio", name=re.compile(r"^斐波那契回撤"))
    expect(fib_tool).to_contain_text("依次点击波段起点和终点")
    fib_tool.click()
    page.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.68)
    page.mouse.click(box["x"] + box["width"] * 0.56, box["y"] + box["height"] * 0.28)
    expect(page.locator(".annotation-list", has_text="斐波那契回撤")).to_be_visible()

    analysis_objects = [
        item
        for item in client.get(
            f"/api/v1/sessions/{session_id}/annotations/dispositions"
        ).json()["dispositions"]
        if item["original_annotation"]["tool"]
        in {"measure", "parallel_channel", "fibonacci_retracement"}
    ]
    assert {item["original_annotation"]["tool"] for item in analysis_objects} == {
        "measure",
        "parallel_channel",
        "fibonacci_retracement",
    }
    page.mouse.click(box["x"] + box["width"] * 0.56, box["y"] + box["height"] * 0.28)
    expect(page.get_by_role("toolbar", name="选中图表对象操作")).to_contain_text(
        "斐波那契回撤"
    )
    page.get_by_role("button", name="删除 斐波那契回撤").click()
    expect(page.locator(".annotation-list button", has_text="deleted")).to_have_count(4)
    client.close()


def test_workbench_shortcuts_are_operational_and_order_keys_remain_drafts(
    page: Page, e2e_stack_factory
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]
    page.goto(f"{stack.web_url}/sessions/{session_id}")
    expect(page.get_by_role("button", name="下一根 K 线")).to_be_visible()

    page.keyboard.press("?")
    expect(page.get_by_role("dialog", name="ReplayTutor 快捷键")).to_be_visible()
    expect(page.get_by_text("交易键只预填模拟订单草稿")).to_be_visible()
    page.keyboard.press("Escape")

    page.keyboard.press("Alt+T")
    expect(page.locator(".drawing-hud", has_text="趋势线")).to_be_visible()
    page.keyboard.press("Escape")

    page.keyboard.press("1")
    page.keyboard.press("5")
    expect(page.get_by_role("button", name="15m")).to_have_attribute("aria-pressed", "true")

    page.get_by_role("button", name="四图").click()
    expect(page.locator(".chart-pane")).to_have_count(4)
    second_chart = page.locator(".chart-pane").nth(1)
    second_chart.get_by_role("button", name="4h").click()
    expect(second_chart.get_by_role("button", name="4h")).to_have_attribute(
        "aria-pressed", "true"
    )
    page.keyboard.press("Control+S")
    expect(page.locator(".shortcut-notice")).to_contain_text("图表布局已保存到本机")
    page.reload()
    expect(page.locator(".chart-pane")).to_have_count(4)
    expect(
        page.locator(".chart-pane").nth(1).get_by_role("button", name="4h")
    ).to_have_attribute("aria-pressed", "true")

    page.keyboard.press("Control+K")
    expect(page.get_by_role("dialog", name="快速搜索功能和工具")).to_be_visible()
    page.keyboard.press("Escape")

    page.keyboard.press("Shift+S")
    expect(page.locator(".shortcut-notice")).to_contain_text("请先锁定交易计划")
    session_after_shortcut = client.get(f"/api/v1/sessions/{session_id}").json()
    assert session_after_shortcut["execution"]["orders"] == []
    client.close()


@pytest.mark.release_acceptance
def test_local_settings_responsive_layout_and_axe(
    page: Page, e2e_stack_factory
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    for width in (1180, 1440, 1920):
        page.set_viewport_size({"width": width, "height": 1000})
        page.goto(f"{stack.web_url}/settings")
        expect(page.get_by_role("heading", name="本地设置与恢复")).to_be_visible()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )

    page.get_by_role("button", name="创建数据库备份").click()
    expect(page.locator(".backup-list code")).to_have_count(1)
    page.get_by_label("AI 模式").select_option("off")
    page.get_by_role("button", name="保存本地偏好").click()
    expect(page.get_by_label("AI 模式")).to_have_value("off")

    axe_path = (
        Path(__file__).resolve().parents[2]
        / "apps"
        / "web"
        / "node_modules"
        / "axe-core"
        / "axe.min.js"
    )
    page.add_script_tag(path=axe_path)
    violations = page.evaluate(
        """async () => (await axe.run(document, {
          runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa']}
        })).violations.filter((item) => ['serious', 'critical'].includes(item.impact))"""
    )
    assert violations == [], [
        (
            violation["id"],
            [
                {"target": node["target"], "html": node["html"]}
                for node in violation["nodes"]
            ],
        )
        for violation in violations
    ]
