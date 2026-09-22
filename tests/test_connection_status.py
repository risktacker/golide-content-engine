from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from golide_engine.connection_status import verify_provider


class ConnectionStatusTests(unittest.TestCase):
    def test_missing_instagram_credentials_are_needs_attention(self):
        with patch.dict(os.environ, {}, clear=True):
            result = verify_provider("instagram")
        self.assertFalse(result["connected"])
        self.assertEqual("needs_attention", result["status"])
        self.assertEqual("instagram", result["platform"])

    def test_missing_youtube_token_is_needs_attention(self):
        with patch.dict(os.environ, {}, clear=True):
            result = verify_provider("youtube")
        self.assertFalse(result["connected"])
        self.assertEqual("needs_attention", result["status"])

    def test_unsupported_provider_rejected(self):
        with self.assertRaises(ValueError):
            verify_provider("x")


if __name__ == "__main__":
    unittest.main()
