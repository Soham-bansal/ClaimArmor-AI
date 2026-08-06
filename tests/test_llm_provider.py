from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from app.services.llm import enhance_explanation


class LlmProviderTests(unittest.TestCase):
    @patch.dict(os.environ, {"CLAIMARMOR_LLM_MODE": "gemini", "GEMINI_API_KEY": "test-key", "GEMINI_EXPLANATION_MODEL": "gemini-test"}, clear=False)
    @patch("httpx.post")
    def test_gemini_provider_parses_text(self, post: Mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Evidence-based explanation"}]}}]}
        post.return_value = response
        text, metadata = enhance_explanation({"evidence": []}, "fallback")
        self.assertEqual(text, "Evidence-based explanation")
        self.assertEqual(metadata, {"mode": "gemini", "used": True, "model": "gemini-test"})
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")

    @patch.dict(os.environ, {"CLAIMARMOR_LLM_MODE": "gemini", "GEMINI_API_KEY": ""}, clear=False)
    def test_gemini_without_key_falls_back(self):
        text, metadata = enhance_explanation({}, "fallback")
        self.assertEqual(text, "fallback")
        self.assertFalse(metadata["used"])


if __name__ == "__main__":
    unittest.main()
