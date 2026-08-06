from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def capture(base_url: str, output: Path, edge: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.goto(base_url, wait_until="networkidle")
        page.screenshot(path=str(output / "01-login.png"), full_page=True)

        page.locator("#loginUser").fill("reviewer")
        page.locator("#loginPassword").fill("Review123!")
        page.get_by_role("button", name="Sign in").click()
        page.locator("#appShell:not(.hidden)").wait_for()
        page.locator("#evaluation table").wait_for()
        page.screenshot(path=str(output / "02-operations-dashboard.png"), full_page=True)

        page.locator("#c-CLM-HOLD-001").click()
        page.get_by_role("button", name="Run investigation").click()
        page.get_by_role("heading", name="Recommendation").wait_for(timeout=30_000)
        page.locator("#workspace").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "03-claim-investigation.png"), full_page=True)
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture real ClaimArmor demo screenshots")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--edge", type=Path, default=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"))
    args = parser.parse_args()
    if not args.edge.exists():
        raise SystemExit(f"Edge executable not found: {args.edge}")
    capture(args.base_url, args.output, args.edge)
    print(f"Screenshots written to {args.output}")


if __name__ == "__main__":
    main()

