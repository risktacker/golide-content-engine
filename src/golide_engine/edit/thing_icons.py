"""What a word on a 3D metaphor looks like (owner 2026-11-26): "apps and models: the real logo if known; data shows
something like a chat even if it's from a news feed; if not known, there are better icons that match well", and the
word "prompt" is never written on screen: the written prompt itself is shown instead.

`picture(word)` -> {"kind": "logo", "svg", "color"} for a real brand (Simple Icons, its own colour), {"kind": "icon",
"svg"} for a matching line icon (Tabler, MIT), {"kind": "prompt"} for a prompt, or None (the word alone).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

# the words people say for kinds of things, and the picture that shows each best
KINDS = {
    "data": "messages", "dataset": "messages", "datasets": "messages", "chat": "messages", "chats": "messages",
    "conversation": "messages", "conversations": "messages", "messages": "messages", "message": "messages",
    "feed": "news", "news": "news", "posts": "news", "post": "news", "articles": "news",
    "model": "brain", "models": "brain", "llm": "brain", "llms": "brain", "ai": "sparkles",
    "app": "apps", "apps": "apps", "tool": "apps", "tools": "apps",
    "docs": "file-text", "doc": "file-text", "documents": "file-text", "document": "file-text", "pdf": "file-text",
    "emails": "mail", "email": "mail", "inbox": "mail",
    "build": "hammer", "fix": "tool", "people": "users", "users": "users", "customers": "users", "team": "users",
    "cost": "coin", "costs": "coin", "price": "coin", "money": "coin", "fees": "coin", "revenue": "chart-line",
    "growth": "chart-line", "accuracy": "target", "goal": "target", "code": "code", "agent": "robot", "agents": "robot",
    "servers": "server", "server": "server", "cloud": "cloud", "security": "shield", "speed": "gauge", "time": "clock",
    "search": "search", "answer": "message-chatbot", "answers": "message-chatbot", "ship": "rocket", "launch": "rocket",
    "learn": "school", "test": "flask", "tests": "flask", "idea": "bulb", "ideas": "bulb", "video": "video",
    "videos": "video", "images": "photo", "image": "photo", "access": "lock-open", "hidden": "eye",
    # 2026-11-27 (owner: "docs, slides, design" showed one wrong "Slides" brand tile): kinds of work are their icons
    "slides": "presentation", "slide": "presentation", "deck": "presentation", "decks": "presentation",
    "presentation": "presentation", "presentations": "presentation", "design": "palette", "designs": "palette",
    "sheets": "table", "sheet": "table", "spreadsheet": "file-spreadsheet", "spreadsheets": "file-spreadsheet",
    "excel": "file-spreadsheet", "whiteboard": "chalkboard", "whiteboards": "chalkboard", "motion": "movie",
    "animation": "movie", "animations": "movie", "explainer": "movie", "explainers": "movie", "crm": "address-book",
    "dashboard": "layout-dashboard", "dashboards": "layout-dashboard", "tracker": "list-check", "trackers": "list-check",
    "checklist": "checklist", "checklists": "checklist", "onboarding": "user-plus", "hiring": "user-plus",
    "quiz": "help", "quizzes": "help", "training": "school", "kpi": "chart-bar", "kpis": "chart-bar",
    "report": "chart-bar", "reports": "chart-bar", "link": "link", "links": "link", "login": "login",
    "backend": "server", "database": "database", "desktop": "device-desktop", "permissions": "key", "permission": "key",
    "risk": "alert-triangle", "risks": "alert-triangle", "lock-in": "lock", "subscription": "credit-card",
}
# brands Simple Icons no longer carries, drawn by their kind (never a look-alike mark)
NO_MARK = {"chatgpt": "message-chatbot", "openai": "sparkles", "gpt": "message-chatbot", "copilot": "sparkles"}
PROMPT = re.compile(r"\bprompts?\b", re.I)


def _tabler_svg(name: str) -> str | None:
    from ..vector import icons
    item = icons.library().get(name)
    if not item:
        return None
    parts = "".join(f'<{tag} ' + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + "/>" for tag, attrs in item["e"])
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{parts}</svg>')


@lru_cache(maxsize=512)
def picture(word: str) -> str:
    """JSON of the picture for a word (cached; JSON so the cache holds plain strings)."""
    w = " ".join(str(word or "").split())
    if not w:
        return "null"
    if PROMPT.search(w):
        return json.dumps({"kind": "prompt"})
    low = w.lower()
    if low in NO_MARK:
        return json.dumps({"kind": "icon", "svg": _tabler_svg(NO_MARK[low])})
    if low in KINDS and _tabler_svg(KINDS[low]):
        # a plain kind of thing ("slides", "sheets") is its icon, never a company that happens to share the word
        return json.dumps({"kind": "icon", "svg": _tabler_svg(KINDS[low])})
    try:                                     # a real brand: its own mark in its own colour
        from ..vector import logos
        hit = logos.find(w)
    except Exception:                        # noqa: BLE001 - no catalogue on this machine: icons only
        hit = None
    if hit and hit.get("svg"):
        svg = re.sub(r"<title>.*?</title>", "", hit["svg"])
        return json.dumps({"kind": "logo", "svg": svg, "color": "#" + str(hit.get("hex") or "E8C268")})
    words = re.findall(r"[a-z0-9]+", low)
    for t in words[::-1]:                    # the head noun is usually last ("hidden fees" -> fees)
        if t in KINDS and _tabler_svg(KINDS[t]):
            return json.dumps({"kind": "icon", "svg": _tabler_svg(KINDS[t])})
    from ..vector import icons
    for cand in (w, w.rstrip("s")):
        name = icons.find_icon(cand, loose=False)
        if name and _tabler_svg(name):
            return json.dumps({"kind": "icon", "svg": _tabler_svg(name)})
    return "null"


def pictures(data: dict) -> dict:
    """The pictures for a metaphor's words: {"left": ..., "right": ..., "label": ..., "item0": ...}."""
    out = {}
    for k in ("left", "right", "label"):
        p = json.loads(picture(data.get(k) or ""))
        if p:
            out[k] = p
    for i, it in enumerate(data.get("items") or []):
        p = json.loads(picture(it))
        if p:
            out[f"item{i}"] = p
    return out
