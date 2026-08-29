from __future__ import annotations

import json

from .base import ProviderOutput
from .openai_client import client, usage_from_response


class OpenAITextProvider:
    def __init__(self, model: str = "gpt-5.6-sol", reasoning_effort: str = "high"):
        self.model = model
        self.reasoning_effort = reasoning_effort

    def _run(self, instructions: str, content: str, web_search: bool = False, max_output_tokens: int = 12000) -> ProviderOutput:
        kwargs = {
            "model": self.model,
            "reasoning": {"effort": self.reasoning_effort},
            "instructions": instructions,
            "input": content,
            "max_output_tokens": max_output_tokens,
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]
        response = client().responses.create(**kwargs)
        input_tokens, cached, output_tokens = usage_from_response(response)
        return ProviderOutput(response.output_text, response.id, input_tokens, cached, output_tokens)

    def generate_json(self, instructions: str, content: str, schema: dict, web_search: bool = False, max_output_tokens: int = 12000) -> ProviderOutput:
        kwargs = {
            "model": self.model,
            "reasoning": {"effort": self.reasoning_effort},
            "instructions": instructions,
            "input": content,
            "max_output_tokens": max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": "golide_output", "strict": True, "schema": schema}},
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]
        response = client().responses.create(**kwargs)
        input_tokens, cached, output_tokens = usage_from_response(response)
        return ProviderOutput(json.loads(response.output_text), response.id, input_tokens, cached, output_tokens)

    def research(self, brief: str) -> ProviderOutput:
        return self._run(
            "Build an evidence-led research packet. Separate verified claims from inference; include source URLs and dates.",
            brief,
            web_search=True,
        )

    def write_script(self, brief: str, research_packet: str) -> ProviderOutput:
        return self._run(
            "Write an original G$LIDE explainer script. Use a high-curiosity opening, mature energetic narration, clear causal steps, and a final question that loops naturally into the opening. Never invent facts.",
            f"BRIEF\n{brief}\n\nRESEARCH\n{research_packet}",
        )
