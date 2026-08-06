from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.schemas import ClaimInput
from app.seed import DEMO_CLAIMS
from app.services.pipeline import investigate


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict("os.environ", {"CLAIMARMOR_LLM_MODE": "offline"})
        self.env_patcher.start()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "test.db"
        db.init_db()

    def tearDown(self):
        self.env_patcher.stop()
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def run_claim(self, index: int):
        claim = ClaimInput.model_validate(DEMO_CLAIMS[index]).model_dump(mode="json")
        return investigate(claim)

    def test_safe_claim_is_cleared(self):
        result = self.run_claim(0)
        self.assertEqual(result.route.value, "CLEAR")
        self.assertEqual(result.recommended_primary_payer, "EMPLOYER_PLAN")

    def test_accident_claim_is_held(self):
        result = self.run_claim(1)
        self.assertEqual(result.route.value, "HOLD")
        self.assertEqual(result.recommended_primary_payer, "AUTO_INSURER")
        self.assertTrue(result.evidence)

    def test_dual_coverage_claim_requires_review(self):
        result = self.run_claim(2)
        self.assertEqual(result.route.value, "HUMAN_REVIEW")
        self.assertTrue(any(rule["rule_id"] == "MSP-DUAL-001" for rule in result.rules))


if __name__ == "__main__":
    unittest.main()
