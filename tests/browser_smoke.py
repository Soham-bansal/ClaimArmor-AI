from playwright.sync_api import sync_playwright
import time


BASE = "http://127.0.0.1:8765"


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f"{BASE}/react/", wait_until="networkidle")
    page.get_by_role("button", name="Sign in").click()
    page.get_by_role("button", name="+ Add new claim").click()
    claim_id = f"CLM-BROWSER-{int(time.time())}"
    page.locator('input[name="claim_id"]').fill(claim_id)
    page.get_by_role("button", name="Create claim", exact=True).click()
    page.get_by_text(f"Created {claim_id}.").wait_for(timeout=10_000)
    assert page.get_by_text("Upload CSV", exact=True).is_visible()
    assert page.get_by_text("Upload EDI-like", exact=True).is_visible()
    page.get_by_role("button", name="CLM-HOLD-001 Rohan Kappor").click()
    page.get_by_role("button", name="Run controlled investigation").click()
    page.get_by_text("HOLD", exact=True).wait_for(timeout=20_000)
    assert "AUTO_INSURER" in page.locator("body").inner_text()
    assert "Seven-agent trace" in page.locator("body").inner_text()
    browser.close()

print("React browser smoke test passed: login -> create -> ingestion controls -> investigate -> cited HOLD result")
