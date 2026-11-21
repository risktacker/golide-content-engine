"""Text that is part of a drawing (a phone's feed, a comment card, a sign, a "zzz") is art, not the story's words:
the collision check (stickman/collide.py) measures only the story's own text. Our drawings run inside art()."""
from __future__ import annotations

import functools


def art(fn):
    @functools.wraps(fn)
    def run(*a, **k):
        from engine import kit
        kit._art_depth = getattr(kit, "_art_depth", 0) + 1
        try:
            return fn(*a, **k)
        finally:
            kit._art_depth -= 1
    return run
