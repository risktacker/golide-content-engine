from __future__ import annotations

import json

from .base import ProviderOutput
from .openai_client import client, usage_from_response


# The output budget includes the model's hidden reasoning, so a busy prompt (web search,
# headlines, long schemas) can run out mid-answer. 2026-10-19: the topic finder was cut
# off at 3,000 tokens and the short failed. A cut-off answer is now retried with a
# bigger budget instead of failing.
MAX_OUTPUT_CAP = 32000
BUDGET_RETRIES = 2


def _cut_off(response) -> bool:
    if getattr(response, "status", None) != "incomplete":
        return False
    details = getattr(response, "incomplete_details", None)
    reason = getattr(details, "reason", None) if details is not None else None
    return reason in (None, "max_output_tokens")


def _create(kwargs: dict):
    """One Responses call; a cut-off answer is retried with double the output budget."""
    response = client().responses.create(**kwargs)
    for _ in range(BUDGET_RETRIES):
        if not _cut_off(response) or kwargs["max_output_tokens"] >= MAX_OUTPUT_CAP:
            break
        kwargs = {**kwargs, "max_output_tokens": min(MAX_OUTPUT_CAP, kwargs["max_output_tokens"] * 2)}
        print(json.dumps({"status": "output_budget_raised", "max_output_tokens": kwargs["max_output_tokens"]}))
        response = client().responses.create(**kwargs)
    return response


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
        response = _create(kwargs)
        input_tokens, cached, output_tokens = usage_from_response(response)
        return ProviderOutput(response.output_text, response.id, input_tokens, cached, output_tokens)

    def generate_json(self, instructions: str, content: str, schema: dict, web_search: bool = False,
                      max_output_tokens: int = 12000, reasoning_effort: str | None = None) -> ProviderOutput:
        kwargs = {
            "model": self.model,
            "reasoning": {"effort": reasoning_effort or self.reasoning_effort},
            "instructions": instructions,
            "input": content,
            "max_output_tokens": max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": "golide_output", "strict": True, "schema": schema}},
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]
        response = _create(kwargs)
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
            """Write ONLY the words the G$LIDE narrator will actually speak. The owner reads this aloud in his own recorded voice, so never include production directions, labels, markdown headings, bullets, scene numbers, camera notes, visual notes, SFX notes, music notes, citations, source URLs, or prefixes such as Narrator:, Script:, Visual:, Scene:, Camera:, Shot:, B-roll:, Caption:, Music:, SFX:, or Transition:.

VOICE: sound like a confident human expert speaking naturally in his own voice: calm, grounded, slightly bassy in feel, eloquent and easy to understand. Never sound like a research paper, corporate copy, a bot, or a theatrical trailer. Prefer ordinary language over technical language. Mix short and medium sentences. Use contractions when natural. Use commas, full stops, questions, dashes and occasional ellipses deliberately so the spoken performance has breathing room, emphasis and feeling. Do not over-dramatize every sentence.

CURIOSITY: do not explain the title or core mechanism immediately. Open with a concrete consequence, contradiction, observation or question. Create a sequence of unanswered questions and partial answers so each section naturally makes the viewer want the next one. The first 30 seconds must establish why the mystery matters without fully resolving it. Use genuine questions and short pauses, but do not use repetitive clickbait phrases.

ANCHOR CONCEPTS: identify 2 to 4 essential technical terms internally. Introduce each term before defining it. First make the viewer see why the term matters, let the uncertainty sit for a while, then later pay it off using a very simple analogy or example and connect that definition back to what the viewer has already seen. Never front-load dictionary definitions. The most important concept should receive its clearest simple-language payoff late in the explanation, before the final conclusion.

EXPLANATION: one thought at a time. Explain cause and effect visually and conversationally. Technical precision still matters; never invent facts or imply evidence that the research packet does not support. If a technical term is unavoidable, explain it in plain language. Use occasional natural viewer-facing lines such as a question or 'think about that' only when they genuinely improve the flow.

STRUCTURE: hook -> stakes -> mystery -> evidence/mechanism in progressive steps -> delayed simple definitions of anchor concepts -> reveal/consequence -> concise resolution -> final question that loops naturally toward the opening. Return plain spoken narration only.""",
            f"BRIEF\n{brief}\n\nRESEARCH\n{research_packet}",
        )
