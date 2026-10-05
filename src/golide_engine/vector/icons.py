"""Topic line-art for GOLIDE Black videos.

The reference video is a *method*, not a template: whatever the narration is
about is what appears on screen (a brain for "brain", a server rack for
"data center", a water drop for "liquid"). Drawings come from the Tabler
outline set (MIT, ~5,000 single-weight line icons, see
assets/icons/LICENSE-tabler.txt) so every subject shares one clean style.

The script model names plain subjects ("server", "water drop"); this module
maps them to drawings locally, so no icon catalogue is sent to the model.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / "assets/icons/tabler-outline.json"

STOPWORDS = set("""
a an the and or but if then than that this these those is are was were be been being it its
of to in on at by for with from into onto over under about as not no just only very more most
less much many few some any all each every one two three four five six seven eight nine ten
you your we our they their he she his her i me my what which who whom why how when where
do does did done can could will would should may might must have has had get gets got make
makes made like also still even so too up down out off again new now here there way thing
things people person lot lots per need needs use uses used using keep keeps
""".split())

# Words people say mapped to the drawing that shows them best.
SYNONYMS = {
    "ai": "brain", "artificial": "brain", "intelligence": "brain", "model": "brain",
    "llm": "message-chatbot", "chatbot": "message-chatbot", "agent": "robot", "agents": "robot",
    "data": "database", "datacenter": "server", "center": "server", "centers": "server",
    "computing": "cpu", "compute": "cpu", "chip": "cpu", "chips": "cpu", "gpu": "cpu", "processor": "cpu",
    "rack": "server-2", "racks": "server-2", "nvidia": "cpu",
    "heat": "flame", "hot": "flame", "warm": "temperature", "temperature": "temperature",
    "cool": "snowflake", "cooling": "snowflake", "cold": "snowflake",
    "liquid": "droplet", "water": "droplet", "fluid": "droplet",
    "air": "wind", "fan": "propeller", "power": "bolt", "energy": "bolt", "electricity": "bolt",
    "kilowatts": "bolt", "watts": "bolt",
    "phone": "device-mobile", "mobile": "device-mobile", "smartphone": "device-mobile",
    "computer": "device-laptop", "laptop": "device-laptop", "desktop": "device-desktop",
    "sun": "sun", "space": "planet", "moon": "moon", "planet": "planet",
    "house": "home", "home": "home", "blanket": "bed", "money": "coin", "cash": "cash",
    "job": "briefcase", "jobs": "briefcase", "work": "briefcase", "career": "briefcase",
    "hire": "user-check", "hired": "user-check", "hiring": "user-check",
    "cv": "file-cv", "resume": "file-cv", "email": "mail", "message": "message",
    "time": "clock", "fast": "rocket", "speed": "gauge", "growth": "trending-up",
    "grow": "trending-up", "decline": "trending-down", "security": "shield-lock",
    "safe": "shield-check", "risk": "alert-triangle", "danger": "alert-triangle",
    "permission": "key", "permissions": "key", "access": "key", "lock": "lock",
    "idea": "bulb", "learn": "school", "learning": "school", "student": "school",
    "world": "world", "global": "world", "internet": "world-www", "cloud": "cloud",
    "code": "code", "software": "code", "app": "apps", "apps": "apps",
    "team": "users-group", "users": "users", "customer": "user", "customers": "users",
    "market": "building-store", "shop": "building-store", "business": "building-skyscraper",
    "company": "building-skyscraper", "factory": "building-factory", "city": "building-community",
    "car": "car", "battery": "battery-charging", "network": "network", "connection": "plug-connected",
    "search": "search", "camera": "camera", "video": "video", "music": "music", "voice": "microphone",
    "eye": "eye", "watch": "eye", "health": "heartbeat", "heart": "heart", "doctor": "stethoscope",
    "trade": "chart-candle", "trading": "chart-candle", "stock": "chart-line", "price": "tag",
    "gold": "coin", "bank": "building-bank", "law": "scale", "rule": "gavel", "rules": "gavel",
    "limit": "barrier-block", "limits": "barrier-block", "boundary": "barrier-block",
    "approval": "circle-check", "approve": "circle-check", "log": "list-details", "logs": "list-details",
    "mistake": "bug", "error": "bug", "fail": "x", "success": "trophy", "win": "trophy",
    "goal": "target", "focus": "target", "plan": "map", "path": "route", "future": "telescope",
}


PHRASES = {
    "data center": "server-2", "data centers": "server-2", "server rack": "server-2",
    "liquid cooling": "droplet", "air cooling": "wind", "machine learning": "brain",
    "social media": "brand-instagram", "job search": "briefcase", "solar panel": "solar-panel",
    "electric car": "car", "credit card": "credit-card", "smart phone": "device-mobile",
}


@lru_cache(maxsize=1)
def library() -> dict:
    return json.loads(LIBRARY.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _index() -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for name, item in library().items():
        if name.endswith("-off") or "-off-" in name:
            continue
        words = set(name.split("-")) | {str(t).lower() for t in item.get("t", [])}
        for word in words:
            index.setdefault(word, set()).add(name)
    return index


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 1]


def find_icon(subject: str, loose: bool = True) -> str | None:
    """Best drawing for a spoken subject ("water drop", "server", "AI").

    ``loose`` also searches the drawings' tags; it is used for subjects the
    script model named on purpose, not for every word of a sentence.
    """
    lib = library()
    words = _tokens(subject)
    slug = "-".join(words)
    phrase = " ".join(words)
    if PHRASES.get(phrase) in lib:
        return PHRASES[phrase]
    if len(words) == 1 and SYNONYMS.get(slug) in lib:
        return SYNONYMS[slug]
    if slug in lib:
        return slug
    for word in words:
        mapped = SYNONYMS.get(word)
        if mapped and mapped in lib:
            return mapped
        if word in lib:
            return word
    if not loose:
        return None
    index = _index()
    scores: dict[str, float] = {}
    for word in words:
        for name in index.get(word, ()):
            parts = name.split("-")
            score = 3.0 if word in parts else 1.0
            score -= 0.15 * (len(parts) - 1)  # prefer simple, generic drawings
            scores[name] = scores.get(name, 0.0) + score
    if not scores:
        return None
    return max(sorted(scores), key=lambda name: scores[name])


def icons_for(subjects: list[str], text: str = "", limit: int = 4) -> list[str]:
    """Drawings for a line: named subjects first, then nouns from the words."""
    found: list[str] = []
    for subject in subjects:
        name = find_icon(subject)
        if name and name not in found:
            found.append(name)
    if len(found) < 1 and text:
        for word in _tokens(text):
            name = find_icon(word, loose=False)
            if name and name not in found:
                found.append(name)
            if len(found) >= limit:
                break
    return found[:limit]


@lru_cache(maxsize=2048)
def polylines(name: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    """The drawing as polylines in a 24x24 box, ready for draw-on animation."""
    from svgelements import Path as SvgPath

    lines = []
    for kind, attrs in library()[name]["e"]:
        if kind != "path" or not attrs.get("d"):
            continue
        path = SvgPath(attrs["d"])
        for sub in path.as_subpaths():
            sub = SvgPath(sub)
            length = sub.length(error=1e-3)
            steps = max(2, int(length * 3))
            points = [sub.point(i / steps) for i in range(steps + 1)]
            pts = tuple((float(p.x), float(p.y)) for p in points if p is not None)
            if len(pts) >= 2:
                lines.append(pts)
    return tuple(lines)
