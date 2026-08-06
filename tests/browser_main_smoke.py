from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:8765/", wait_until="networkidle")
    page.get_by_role("button", name="Sign in").click()
    scenario_panel = page.get_by_text("Prepared claim scenarios", exact=True).locator("xpath=ancestor::div[contains(@class,'card')]")
    page.locator("#claims .claim").first.wait_for(timeout=10_000)
    assert page.locator("#claims .claim").count() == 4
    for route in ("CLEAR", "HOLD", "HUMAN REVIEW", "UNDETERMINED"):
        assert route in scenario_panel.inner_text()
    page.get_by_role("button", name="Create one claim").click()
    assert page.locator("#newPayer option").all_text_contents() == ["Employer plan", "Medicare", "Auto insurer"]
    assert page.locator("#newPayer").input_value() == "EMPLOYER_PLAN"
    page.get_by_role("button", name="Cancel").click()
    page.get_by_text("CLM-HOLD-001", exact=True).click()
    page.get_by_role("button", name="Run investigation").click()
    page.get_by_text("Decision comparison", exact=True).wait_for(timeout=20_000)
    comparison = page.get_by_text("Decision comparison", exact=True).locator("xpath=ancestor::div[contains(@class,'card')]").inner_text()
    assert "Deterministic rules" in comparison
    assert "HOLD" in comparison
    assert "Proposed primary payer" in comparison
    assert "AUTO_INSURER" in comparison
    browser.close()

print("Main dashboard decision-comparison smoke test passed")
