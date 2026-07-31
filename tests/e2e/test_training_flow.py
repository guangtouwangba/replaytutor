from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
import time

import pytest
from playwright.sync_api import Page, expect

from .conftest import E2EStack
from .helpers import command_id, create_training_session


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
        == "0012_local_hardening"
    )

    page.goto(f"{stack.web_url}/data")
    expect(page.get_by_role("heading", name="数据中心")).to_be_visible()
    page.get_by_role("button", name="载入真实 BTC 样例").click()
    expect(page.get_by_text("44,640", exact=True).first).to_be_visible(timeout=30_000)

    page.goto(f"{stack.web_url}/setup")
    page.get_by_role("button", name="创建训练会话").click()
    expect(page.get_by_role("heading", name="先锁定交易计划")).to_be_visible(
        timeout=30_000
    )
    session_id = page.url.rstrip("/").split("/")[-1]

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

    page.get_by_label("向 Codex 询问当前 frame").fill("为复盘生成独立 AI 证据")
    page.get_by_role("button", name="让 Codex 检查").click()
    expect(page.get_by_text("AI 图上标注", exact=True)).to_be_visible(timeout=30_000)
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

    page.get_by_label("标注文字").first.fill("E2E 趋势线")
    page.get_by_title("趋势线").click()
    chart = page.locator(".replay-chart")
    box = chart.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.45)
    page.mouse.click(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.35)
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

    page.get_by_label("标注文字").first.fill("E2E 矩形")
    page.get_by_title("矩形").click()
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
    page.get_by_title("矩形").click()
    page.mouse.click(box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.5)
    page.keyboard.press("Escape")
    page.wait_for_timeout(250)
    after_count = len(
        client.get(f"/api/v1/sessions/{session_id}/annotations/dispositions").json()[
            "dispositions"
        ]
    )
    assert after_count == before_count
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
