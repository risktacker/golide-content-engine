"""A model answer cut off by the output budget is retried bigger, never parsed half-done (2026-10-19)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from golide_engine.providers import openai_text
from golide_engine.providers.openai_text import OpenAITextProvider


def _response(text, status="completed", reason=None):
    details = SimpleNamespace(reason=reason) if reason else None
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, input_tokens_details=SimpleNamespace(cached_tokens=0),
                            output_tokens_details=SimpleNamespace(reasoning_tokens=0))
    return SimpleNamespace(output_text=text, id="r1", status=status, incomplete_details=details, usage=usage)


class OutputBudgetTests(unittest.TestCase):
    def _provider(self, responses):
        calls = []

        def create(**kwargs):
            calls.append(kwargs["max_output_tokens"])
            return responses.pop(0)

        fake = SimpleNamespace(responses=SimpleNamespace(create=create))
        return calls, mock.patch.object(openai_text, "client", lambda: fake)

    def test_cut_off_json_is_retried_with_double_budget(self):
        calls, patch = self._provider([_response('{"candidates": [{"title": "Unterminat', "incomplete",
                                                 "max_output_tokens"), _response('{"ok": true}')])
        with patch:
            out = OpenAITextProvider().generate_json("i", "c", {"type": "object"}, max_output_tokens=3000)
        self.assertEqual({"ok": True}, out.value)
        self.assertEqual([3000, 6000], calls)

    def test_complete_answer_is_not_retried(self):
        calls, patch = self._provider([_response('{"ok": 1}')])
        with patch:
            OpenAITextProvider().generate_json("i", "c", {"type": "object"}, max_output_tokens=3000)
        self.assertEqual([3000], calls)

    def test_budget_never_passes_the_cap(self):
        cut = lambda: _response('{"a', "incomplete", "max_output_tokens")  # noqa: E731
        calls, patch = self._provider([cut(), cut(), cut()])
        with patch, self.assertRaises(ValueError):
            OpenAITextProvider().generate_json("i", "c", {"type": "object"}, max_output_tokens=20000)
        self.assertEqual([20000, 32000], calls)


if __name__ == "__main__":
    unittest.main()
