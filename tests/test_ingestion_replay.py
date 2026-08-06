from __future__ import annotations

import unittest

from app.services.ingestion import encode_synthetic_837, parse_synthetic_837


class IngestionTests(unittest.TestCase):
    def test_edi_like_round_trip(self):
        source = {"claim_id": "CLM-EDI-TEST", "member_id": "MBR-1002", "member_name": "Rohan Kapoor", "member_dob": "1988-11-03", "service_date": "2026-08-05", "amount": 20000, "submitted_payer": "EMPLOYER_PLAN", "accident_related": True}
        parsed = parse_synthetic_837(encode_synthetic_837(source))
        self.assertEqual(parsed[0].claim_id, source["claim_id"])
        self.assertTrue(parsed[0].accident_related)

    def test_invalid_edi_like_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_synthetic_837("INVALID*NOT*A*CLAIM*SEGMENT~")


if __name__ == "__main__":
    unittest.main()
