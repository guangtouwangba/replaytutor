from __future__ import annotations

from playwright.sync_api import Page, expect

from .conftest import E2EStack
from .helpers import create_training_session


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
    expect(page.locator(".context-tray")).to_contain_text("server evidence")
    page.get_by_label("Ask Codex about the current frame").fill(
        "Explain the selected moving average using only signed evidence."
    )
    page.get_by_role("button", name="Ask Codex to check").click()
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
