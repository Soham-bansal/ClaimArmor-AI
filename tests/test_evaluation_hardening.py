from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import db
from app.evaluation import evaluate
from app.services.business import simulate_roi


class EvaluationAndHardeningTests(unittest.TestCase):
    def test_comparative_evaluation_uses_holdout(self):
        result = evaluate(output_path=None)
        self.assertEqual(result["dataset_rows"], 3000)
        self.assertEqual(result["evaluation_rows"], 660)
        self.assertEqual(len(result["approaches"]), 3)
        self.assertGreaterEqual(result["retrieval"]["hit_at_4"], 0.8)
        self.assertTrue(all(0 <= item["precision"] <= 1 for item in result["approaches"]))

    def test_roi_is_derived_from_visible_assumptions(self):
        result = simulate_roi({
            "annual_claims": 1000, "average_claim_amount": 1000, "leakage_rate": 0.10,
            "value_detection_rate": 0.80, "review_rate": 0.20, "review_cost": 10,
            "false_positive_rate": 0.05, "false_positive_cost": 20, "annual_platform_cost": 5000,
        })
        self.assertEqual(result["estimated_gross_leakage"], 100000)
        self.assertEqual(result["estimated_prevented_leakage"], 80000)
        self.assertEqual(result["estimated_net_benefit"], 72000)

    def test_audit_chain_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            original = db.DB_PATH
            db.DB_PATH = Path(directory) / "audit.db"
            try:
                db.init_db()
                db.put_claim({"claim_id": "CLM-AUDIT"})
                db.append_audit("CLM-AUDIT", "ONE", {"value": 1})
                db.append_audit("CLM-AUDIT", "TWO", {"value": 2})
                self.assertTrue(db.verify_audit_chain("CLM-AUDIT")["valid"])
                engine = db._engine()
                try:
                    with engine.begin() as connection:
                        connection.execute(db.audit_table.update().where(db.audit_table.c.claim_id == "CLM-AUDIT").values(payload='{"value": 999}'))
                finally:
                    engine.dispose()
                self.assertFalse(db.verify_audit_chain("CLM-AUDIT")["valid"])
            finally:
                db.DB_PATH = original


if __name__ == "__main__":
    unittest.main()
