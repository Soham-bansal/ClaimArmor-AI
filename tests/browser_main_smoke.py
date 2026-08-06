from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:8765/", wait_until="networkidle")
    page.get_by_role("button", name="Sign in").click()
    assert page.get_by_text("Upload EDI-like batch", exact=True).count() == 0
    page.locator("#claims .claim").first.wait_for(timeout=10_000)
    business_details = page.locator("details.secondary-details:not(.model-details)")
    assert business_details.get_attribute("open") is None
    business_details.locator("summary").click()
    assert page.get_by_role("button", name="Calculate scenario").is_visible()
    business_details.locator("summary").click()
    model_details = page.locator("details.model-details")
    assert model_details.get_attribute("open") is None
    assert page.get_by_text("Approach comparison", exact=True).count() == 0
    model_details.locator("summary").click()
    assert page.get_by_text("Trained model performance", exact=True).is_visible()
    assert model_details.locator(".metric").count() == 4
    model_details.locator("summary").click()
    page.evaluate("""reviewQueueItems=Array.from({length:7},(_,i)=>({claim_id:`QUEUE-${i+1}`,route:'HOLD'}));reviewQueuePage=1;renderQueue()""")
    assert page.locator("#queue .claim").count() == 3
    assert "Page 1 of 3" in page.locator("#queue").inner_text()
    page.locator("#queue").get_by_role("button", name="Next").click()
    assert page.locator("#queue .claim").count() == 3
    assert "Page 2 of 3" in page.locator("#queue").inner_text()
    page.locator("#queue").get_by_role("button", name="Next").click()
    assert page.locator("#queue .claim").count() == 1
    assert "Page 3 of 3" in page.locator("#queue").inner_text()
    scenario_panel = page.get_by_text("Prepared claim scenarios", exact=True).locator("xpath=ancestor::div[contains(@class,'card')]")
    assert page.locator("#claims .claim").count() == 4
    for route in ("CLEAR", "HOLD", "HUMAN REVIEW", "UNDETERMINED"):
        assert route in scenario_panel.inner_text()
    page.get_by_role("button", name="Create one claim").click()
    assert page.locator("#newPayer option").all_text_contents() == ["Employer plan", "Medicare", "Auto insurer"]
    assert page.locator("#newPayer").input_value() == "EMPLOYER_PLAN"
    page.get_by_role("button", name="Cancel").click()
    page.locator("#csvFile").set_input_files("data/samples/claims_upload_two_rows.csv")
    page.get_by_role("button", name="Upload CSV").click()
    page.get_by_text("Uploaded claims", exact=True).wait_for(timeout=10_000)
    assert page.locator("#uploadedClaims .uploaded-item").count() == 2
    page.locator("#uploadedClaims .uploaded-item").nth(1).get_by_role("button", name="Open claim").click()
    page.get_by_text("CLM-BATCH-102", exact=True).wait_for(timeout=10_000)
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
