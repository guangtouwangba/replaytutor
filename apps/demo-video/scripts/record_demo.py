from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


def post(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - loopback demo API only
        return json.loads(response.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", choices=("en-US", "zh-CN"), required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--web-url", required=True)
    args = parser.parse_args()
    output_dir = Path(__file__).resolve().parents[1] / "public" / "recordings"
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = post(f"{args.api_url}/api/v1/datasets/golden", {})
    session = post(
        f"{args.api_url}/api/v1/sessions",
        {"snapshot_id": snapshot["snapshot_id"], "start_mode": "beginning", "seed": 7, "warmup_bars": 120, "initial_cash": "100000", "hidden_real_date": True, "playbook_id": None},
    )
    session_id = session["session"]["session_id"]
    scene_checks: list[dict[str, object]] = []

    def assert_page_locale(page, scene: str) -> None:
        visible_text = page.locator("body").inner_text()
        han_samples = sorted(set(re.findall(r"[\u3400-\u9fff]+", visible_text)))
        if args.locale == "en-US" and han_samples:
            raise AssertionError(
                f"English recording contains Chinese UI in {scene}: "
                + ", ".join(han_samples[:12])
            )
        if args.locale == "zh-CN" and not han_samples:
            raise AssertionError(f"Chinese recording has no Chinese UI in {scene}")
        scene_checks.append({
            "scene": scene,
            "url": page.url,
            "html_lang": page.locator("html").get_attribute("lang"),
            "han_sample_count": len(han_samples),
        })
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=output_dir, record_video_size={"width": 1440, "height": 900}, locale=args.locale, timezone_id="UTC")
        page = context.new_page()
        locale_json = json.dumps(args.locale)
        page.add_init_script(
            "localStorage.setItem('replaytutor:locale', "
            f"{locale_json}); localStorage.setItem('replaytutor:locale-preference', "
            f"{locale_json}); localStorage.setItem('replaytutor:onboarding-complete', '1');"
        )
        page.goto(args.web_url, wait_until="networkidle")
        assert_page_locale(page, "home")
        page.wait_for_timeout(3500)
        page.goto(f"{args.web_url}/setup", wait_until="networkidle")
        assert_page_locale(page, "setup")
        page.wait_for_timeout(3500)
        page.goto(f"{args.web_url}/sessions/{session_id}", wait_until="networkidle")
        assert_page_locale(page, "workbench")
        page.wait_for_timeout(9000)
        video = page.video
        context.close()
        assert video is not None
        suffix = "zh" if args.locale == "zh-CN" else "en"
        target = output_dir / f"replaytutor-browser-{suffix}.webm"
        target.unlink(missing_ok=True)
        Path(video.path()).replace(target)
        browser.close()
    manifest = {"schema_version": "1.0", "locale": args.locale, "viewport": [1440, 900], "timezone": "UTC", "snapshot_id": snapshot["snapshot_id"], "session_id": session_id, "contains_private_data": False, "locale_checks": scene_checks}
    (output_dir / f"replaytutor-browser-{suffix}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
