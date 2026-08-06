from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ml.generate import generate_dataset, write_dataset
from app.ml.train import train


class MachineLearningTests(unittest.TestCase):
    def test_generation_is_reproducible(self):
        self.assertEqual(generate_dataset(10, 7), generate_dataset(10, 7))

    def test_training_writes_model_and_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = write_dataset(root / "claims.csv", rows=240, seed=9)
            model = root / "model.joblib"
            metrics_file = root / "metrics.json"
            metrics = train(dataset, model, metrics_file, seed=9)
            self.assertTrue(model.exists())
            self.assertTrue(metrics_file.exists())
            self.assertGreaterEqual(metrics["pr_auc"], 0.60)
            self.assertEqual(metrics["dataset_rows"], 240)


if __name__ == "__main__":
    unittest.main()
