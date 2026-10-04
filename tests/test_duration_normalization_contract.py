import inspect
import unittest

from golide_engine.orchestration import production


class OwnerVoiceIsNeverRetimedTests(unittest.TestCase):
    """Locked 2026-10-04: the owner recording is the master timeline.

    A recording outside its window is rejected for re-recording; it is never
    sped up, slowed down or trimmed to fit.
    """

    def test_no_tempo_correction(self):
        source = inspect.getsource(production.ProductionService.run)
        self.assertNotIn("atempo", source)
        self.assertNotIn("maximum * 1.08", source)

    def test_length_checked_before_transcription(self):
        source = inspect.getsource(production.ProductionService.run)
        check = source.index("check_recording_length")
        transcribe = source.index("transcribe_words")
        self.assertLess(check, transcribe)


if __name__ == "__main__":
    unittest.main()
