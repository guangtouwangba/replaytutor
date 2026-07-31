from __future__ import annotations

# pyright: reportMissingImports=false
import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--screenshot", required=True)
    args = parser.parse_args()

    report = Path(args.report).resolve()
    screenshot = Path(args.screenshot).resolve()
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        launch_options: dict[str, object] = {"headless": True}
        executable_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if executable_path:
            launch_options["executable_path"] = executable_path
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text)
                if message.type == "error"
                else None
            ),
        )
        page.goto(report.as_uri())
        page.wait_for_load_state("networkidle")

        first_episode = page.locator(".episode").first
        episode_count = page.locator(".episode").count()
        assert page.locator(".trade-table tbody tr").count() == episode_count
        assert page.locator(".trade-table .result-badge").count() == episode_count
        assert first_episode.locator(".verdict-band").is_visible()
        assert first_episode.locator(".decision-brief .brief-card").count() == 3
        assert "当时背景" in first_episode.locator(".decision-brief").inner_text()
        assert "开仓点位评价" in first_episode.locator(".decision-brief").inner_text()
        assert "下次怎么做" in first_episode.locator(".decision-brief").inner_text()
        assert first_episode.locator(".trade-chip").count() >= 2
        assert first_episode.locator(".chart-panel.active canvas").is_visible()
        assert first_episode.locator("canvas").first.bounding_box()["height"] >= 500
        assert first_episode.locator("[data-chart-reset]").count() == 1

        canvas = first_episode.locator(".chart-panel.active canvas")
        initial_visible_bars = int(canvas.get_attribute("data-visible-bars"))
        canvas.hover()
        page.mouse.wheel(0, -450)
        page.wait_for_timeout(100)
        zoomed_visible_bars = int(canvas.get_attribute("data-visible-bars"))
        assert zoomed_visible_bars < initial_visible_bars

        box = canvas.bounding_box()
        assert box is not None
        initial_start = int(canvas.get_attribute("data-visible-start"))
        page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.5)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.5)
        page.mouse.up()
        panned_start = int(canvas.get_attribute("data-visible-start"))
        assert panned_start != initial_start

        first_episode.locator("[data-chart-reset]").click()
        assert int(canvas.get_attribute("data-visible-bars")) == initial_visible_bars

        first_episode.locator('[data-tf="15m"]').click()
        assert first_episode.locator('[data-chart-panel="15m"]').is_visible()
        first_episode.locator(".trade-chip").first.click()
        assert first_episode.locator('[data-chart-panel="5m"]').is_visible()
        assert "active" in first_episode.locator(".trade-chip").first.get_attribute(
            "class"
        )

        first_episode.locator('[data-side="evidence"]').click()
        assert first_episode.locator('[data-pane="evidence"]').is_visible()
        canvas_height = first_episode.locator("canvas").first.bounding_box()["height"]
        page.screenshot(path=str(screenshot), full_page=False)
        browser.close()

    assert console_errors == []
    print(
        {
            "episodes": episode_count,
            "canvas_height": canvas_height,
            "zoomed_visible_bars": zoomed_visible_bars,
            "panned_start": panned_start,
            "console_errors": console_errors,
            "screenshot": str(screenshot),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
