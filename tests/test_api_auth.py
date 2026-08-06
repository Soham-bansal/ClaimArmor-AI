from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import db
from app.main import app


class AuthenticatedApiTests(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict("os.environ", {"CLAIMARMOR_LLM_MODE": "offline"})
        self.env_patcher.start()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "api.db"
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.env_patcher.stop()
        self.client_context.__exit__(None, None, None)
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def login(self, username: str, password: str) -> dict:
        response = self.client.post("/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_authentication_and_role_enforcement(self):
        unauthenticated = self.client.get("/api/claims")
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(unauthenticated.headers["x-content-type-options"], "nosniff")
        self.assertEqual(unauthenticated.headers["x-frame-options"], "DENY")
        self.assertTrue(unauthenticated.headers["x-request-id"])
        reviewer = self.login("reviewer", "Review123!")
        response = self.client.post("/api/claims", headers=reviewer, json={
            "claim_id": "CLM-FORBIDDEN", "member_name": "Rohan Kapoor", "member_dob": "1988-11-03",
            "member_id": "MBR-1002", "service_date": "2026-08-05", "amount": 1000,
            "submitted_payer": "EMPLOYER_PLAN"
        })
        self.assertEqual(response.status_code, 403)

    def test_csv_to_review_queue_to_writeback(self):
        analyst = self.login("analyst", "Analyst123!")
        csv_text = "claim_id,member_name,member_dob,member_id,service_date,amount,submitted_payer,claim_type,accident_related,diagnosis_group\nCLM-API-CSV,Rohan Kapoor,1988-11-03,MBR-1002,2026-08-05,22000,EMPLOYER_PLAN,TRAUMA,true,ACCIDENT\n"
        uploaded = self.client.post("/api/claims/upload-csv", headers=analyst, json={"csv_text": csv_text})
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        self.assertEqual(uploaded.json()["summary"]["created"], 1)
        investigated = self.client.post("/api/claims/CLM-API-CSV/investigate", headers=analyst)
        self.assertEqual(investigated.status_code, 200, investigated.text)
        self.assertEqual(investigated.json()["route"], "HOLD")

        reviewer = self.login("reviewer", "Review123!")
        queue = self.client.get("/api/review-queue", headers=reviewer).json()
        self.assertIn("CLM-API-CSV", {item["claim_id"] for item in queue})
        reviewed = self.client.post("/api/investigations/CLM-API-CSV/review", headers=reviewer, json={"reviewer": "ignored", "action": "APPROVE", "reason": "Verified cited accident evidence", "final_route": "HOLD"})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["writeback"]["reviewer"], "reviewer")
        queue_after = self.client.get("/api/review-queue", headers=reviewer).json()
        self.assertNotIn("CLM-API-CSV", {item["claim_id"] for item in queue_after})

    def test_streamed_investigation_emits_real_agent_order_and_result(self):
        analyst = self.login("analyst", "Analyst123!")
        with self.client.stream("POST", "/api/claims/CLM-HOLD-001/investigate-stream", headers=analyst) as response:
            self.assertEqual(response.status_code, 200)
            events = [json.loads(line) for line in response.iter_lines() if line]
        agents = [event["data"]["agent"] for event in events if event["type"] == "agent"]
        self.assertEqual(agents, ["identity_investigator", "coverage_investigator", "policy_researcher", "primacy_reasoner", "verification_critic", "financial_impact", "explanation"])
        self.assertEqual(events[-1]["type"], "complete")
        self.assertEqual(events[-1]["data"]["recommended_primary_payer"], "AUTO_INSURER")


if __name__ == "__main__":
    unittest.main()
