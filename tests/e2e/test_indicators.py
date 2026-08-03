from __future__ import annotations

import re
import time
from datetime import datetime

from playwright.sync_api import Page, expect

from .conftest import E2EStack
from .helpers import create_training_session


def test_price_axis_hover_add_persists_visible_horizontal_line(
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
    chart = page.get_by_label("BTCUSDT 1m replay candlestick chart")
    expect(chart).to_be_visible()
    bounds = chart.bounding_box()
    assert bounds is not None
    page.mouse.move(
        bounds["x"] + bounds["width"] - 20,
        bounds["y"] + bounds["height"] * 0.45,
    )

    add_button = page.get_by_role("button", name=re.compile(r"Open price actions at"))
    expect(add_button).to_be_visible()
    guide = page.locator(".price-axis-guide")
    expect(guide).to_be_visible()
    guide_bounds = guide.bounding_box()
    assert guide_bounds is not None
    assert guide_bounds["width"] > bounds["width"] * 0.7
    first_guide_y = guide_bounds["y"]

    page.mouse.move(
        bounds["x"] + bounds["width"] - 20,
        bounds["y"] + bounds["height"] * 0.55,
    )
    moved_guide_bounds = guide.bounding_box()
    assert moved_guide_bounds is not None
    assert moved_guide_bounds["y"] > first_guide_y
    expect(page.get_by_role("menu", name="Price scale actions")).to_have_count(0)
    page.get_by_role("button", name=re.compile(r"Open price actions at")).click()

    menu = page.get_by_role("menu", name="Price scale actions")
    expect(menu).to_be_visible()
    expect(menu.get_by_role("menuitem")).to_contain_text("Draw horizontal line at")
    menu.get_by_role("menuitem").click()

    deadline = time.monotonic() + 10
    horizontal_line = None
    session = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/sessions/{session_id}")
        response.raise_for_status()
        session = response.json()
        horizontal_line = next(
            (
                annotation
                for annotation in session["annotations"]
                if annotation.get("tool") == "horizontal_line"
                and annotation.get("metadata", {}).get("source") == "price_axis"
            ),
            None,
        )
        if horizontal_line is not None:
            break
        time.sleep(0.1)

    assert session is not None
    assert horizontal_line is not None
    assert len(horizontal_line["points"]) == 1
    assert datetime.fromisoformat(horizontal_line["points"][0]["time"]) <= datetime.fromisoformat(
        session["session"]["frame"]["visible_at"]
    )
    expect(page.locator(".chart-object-actions")).to_be_visible()
    client.close()


def test_indicator_catalog_adds_to_active_chart_and_restores_locally(
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
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{stack.web_url}/sessions/{session_id}")
    trigger = page.get_by_role("button", name="Indicators", exact=True)
    expect(trigger).to_contain_text("1")
    trigger.click()
    expect(page.locator(".indicator-panel")).to_be_visible()
    page.get_by_role("button", name="Add MA", exact=True).click()
    expect(trigger).to_contain_text("2")
    expect(page.locator(".indicator-current")).to_contain_text("Moving Average")
    ma_instance = page.locator(".indicator-instance").filter(has_text="Moving Average")
    ma_instance.get_by_role("button", name="Add to Tutor context").click()
    page.get_by_role("button", name="Close indicators").click()
    page.get_by_role("button", name="Chat", exact=True).click()
    page.get_by_role("button", name=re.compile(r"Chart context")).click()
    expect(page.locator(".context-tray")).to_contain_text("server evidence")
    page.get_by_label("Message Codex Tutor").fill(
        "Explain the selected moving average using only signed evidence."
    )
    page.get_by_role("button", name="Send", exact=True).click()
    expect(page.get_by_text("E2E Tutor 已完成当前证据检查")).to_be_visible(
        timeout=30_000
    )

    page.reload()
    trigger = page.get_by_role("button", name="Indicators", exact=True)
    expect(trigger).to_contain_text("2")
    trigger.click()
    expect(page.locator(".indicator-current")).to_contain_text("Moving Average")
    assert page_errors == []
    client.close()


def test_indicator_legend_collapse_hides_canvas_text_but_keeps_indicator(
    page: Page,
    e2e_stack_factory,
) -> None:
    stack: E2EStack = e2e_stack_factory("fake")
    client, created = create_training_session(stack.api_url)
    session_id = created["session"]["session_id"]
    page.add_init_script(
        "localStorage.setItem('replaytutor:locale', 'en-US'); "
        "localStorage.setItem('replaytutor:locale-preference', 'en-US'); "
        "window.__indicatorCanvasText = []; "
        "const originalFillText = CanvasRenderingContext2D.prototype.fillText; "
        "CanvasRenderingContext2D.prototype.fillText = function(text, ...args) { "
        "window.__indicatorCanvasText.push(String(text)); "
        "return originalFillText.call(this, text, ...args); "
        "};"
    )

    page.goto(f"{stack.web_url}/sessions/{session_id}")
    page.wait_for_function(
        "window.__indicatorCanvasText.some((text) => text.includes('VOL'))"
    )
    page.evaluate("window.__indicatorCanvasText = []")

    page.get_by_role("button", name="Collapse indicator legend").click()
    expect(page.get_by_role("button", name="Expand indicator legend")).to_have_attribute(
        "aria-expanded", "false"
    )
    page.wait_for_timeout(100)

    assert not page.evaluate(
        "window.__indicatorCanvasText.some((text) => text.includes('VOL'))"
    )
    expect(page.get_by_role("button", name="Expand indicator legend")).to_contain_text(
        "1"
    )
    client.close()
