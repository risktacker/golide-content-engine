"""World 3D's own text model client. Kept here so world3d/ imports nothing from src/.
Same model and prices as the engine (config/providers.json, config/provider-pricing.json)."""

from __future__ import annotations

import json
from types import SimpleNamespace

MODEL = "gpt-5.6-luna"
EFFORT = "medium"
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.2, 0.02, 1.2  # dollars per million tokens
PRICE_SEARCH = 0.01  # dollars per web search call
OUTPUT_CAP = 32000


class SpendCapReached(RuntimeError):
    pass


class LunaText:
    """generate_json(...) like the engine's provider, plus a running cost and a hard spend cap."""

    def __init__(self, cap_dollars: float, model: str = MODEL, effort: str = EFFORT):
        from openai import OpenAI
        self.client = OpenAI()
        self.model, self.effort, self.cap = model, effort, cap_dollars
        self.spent = 0.0
        self.calls: list[dict] = []

    def _charge(self, response) -> None:
        u = response.usage
        cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        searches = sum(1 for item in response.output if getattr(item, "type", "") == "web_search_call")
        cost = ((u.input_tokens - cached) * PRICE_IN + cached * PRICE_CACHED + u.output_tokens * PRICE_OUT) / 1e6
        cost += searches * PRICE_SEARCH
        self.spent += cost
        self.calls.append({"input": u.input_tokens, "cached": cached, "output": u.output_tokens,
                           "searches": searches, "dollars": round(cost, 4)})
        print(json.dumps({"status": "world3d_text_call", **self.calls[-1], "total": round(self.spent, 4)}), flush=True)

    def generate_json(self, instructions: str, content: str, schema: dict, web_search: bool = False,
                      max_output_tokens: int = 12000, **_) -> SimpleNamespace:
        if self.spent >= self.cap:
            raise SpendCapReached(f"spend cap ${self.cap:.2f} reached (${self.spent:.4f})")
        kwargs = {
            "model": self.model, "reasoning": {"effort": self.effort}, "instructions": instructions,
            "input": content, "max_output_tokens": max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": "world3d", "strict": True, "schema": schema}},
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]
        while True:
            response = self.client.responses.create(**kwargs)
            self._charge(response)
            cut = response.status == "incomplete" and getattr(response.incomplete_details, "reason", None) in (None, "max_output_tokens")
            if not cut or kwargs["max_output_tokens"] >= OUTPUT_CAP or self.spent >= self.cap:
                break
            kwargs["max_output_tokens"] = min(OUTPUT_CAP, kwargs["max_output_tokens"] * 2)
        return SimpleNamespace(value=json.loads(response.output_text), id=response.id)
