import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from golide_engine.orchestration.production import ProductionService


class StudioBridgeAuthorizationTests(unittest.TestCase):
    def service(self):
        service = ProductionService.__new__(ProductionService)
        service.providers = SimpleNamespace(config={
            "voice": {"provider": "elevenlabs", "approval_status": "approved"}
        })
        return service

    @patch.dict(os.environ, {"GOLIDE_ENABLE_PAID_PRODUCTION": "1"})
    def test_render_only_does_not_require_a_youtube_target(self):
        self.service()._assert_authorized({
            "production_authorized": True,
            "output_destination": "render-only",
            "release": {"approved": True, "channel_id": None},
        })

    @patch.dict(os.environ, {"GOLIDE_ENABLE_PAID_PRODUCTION": "1"})
    def test_upload_still_requires_the_locked_golide_channel(self):
        with self.assertRaisesRegex(RuntimeError, "locked G\\$LIDE channel"):
            self.service()._assert_authorized({
                "production_authorized": True,
                "output_destination": "render-and-upload",
                "release": {"approved": True, "channel_id": "wrong"},
            })

    @patch.dict(os.environ, {"GOLIDE_ENABLE_PAID_PRODUCTION": "1"})
    def test_unknown_destination_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unsupported output destination"):
            self.service()._assert_authorized({
                "production_authorized": True,
                "output_destination": "surprise-me",
                "release": {"approved": True, "channel_id": None},
            })


if __name__ == "__main__":
    unittest.main()
