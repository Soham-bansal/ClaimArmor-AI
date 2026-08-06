from __future__ import annotations

import unittest

from app.data_generation import generate_entity_bundle
from app.identity_evaluation import evaluate_identity


class IdentityTests(unittest.TestCase):
    def test_entity_bundle_contains_planned_domains(self):
        bundle = generate_entity_bundle(20, 5)
        for domain in ("members", "dependants", "employers", "providers", "coverages", "eligibility", "claims", "identity_variants"):
            self.assertIn(domain, bundle)
            self.assertTrue(bundle[domain])
        self.assertTrue(all("expected_primary_payer" in claim for claim in bundle["claims"]))

    def test_identity_metrics_are_measured(self):
        metrics = evaluate_identity(sample_size=8, seed=7, output=None)
        self.assertGreaterEqual(metrics["precision"], 0.8)
        self.assertGreaterEqual(metrics["recall"], 0.7)
        self.assertGreater(metrics["splink_cases"], 0)


if __name__ == "__main__":
    unittest.main()
