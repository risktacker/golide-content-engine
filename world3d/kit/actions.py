"""Actions move or change parts over time. Each returns update(t)."""
import math

from . import materials as mats
from .ease import smooth, span
from .registry import actions


@actions.add("explode")
def explode(model, cfg):
    """Separate parts along the offsets in their blueprint, in order, then hold."""
    a, b = cfg["start"], cfg["end"]
    close = cfg.get("close")
    items = [model.part(p) for p in cfg["parts"]] if "parts" in cfg else list(model.parts.values())

    def update(t):
        u = smooth(span(t, a, b))
        if close:
            u *= 1 - smooth(span(t, close, close + (b - a)))
        for p in items:
            p.group.location = p.home + p.explode * u

    return update


@actions.add("drift")
def drift(model, cfg):
    """Slow free roll of the whole object, so nothing ever sits dead still."""
    base = model.root.rotation_euler.copy()
    rate = math.radians(cfg.get("deg_per_sec", 1.2))

    spin_only = cfg.get("axis") == "z"

    def update(t):
        if spin_only:  # objects standing on a floor turn like a turntable, never roll
            model.root.rotation_euler = (base[0], base[1], base[2] + rate * t)
        else:
            model.root.rotation_euler = (base[0] + rate * t, base[1], base[2] + rate * 0.4 * t)

    return update


@actions.add("glow")
def glow(model, cfg):
    """The named part lights up gold while it is being talked about."""
    part = model.part(cfg["part"])
    targets = [m.data.materials[0] for m in part.meshes]
    a, b, peak = cfg["start"], cfg["end"], cfg.get("strength", 2.5)

    def update(t):
        u = smooth(span(t, a, a + 0.5)) * (1 - smooth(span(t, b - 0.5, b)))
        for m in targets:
            mats.set_glow(m, peak * u)

    return update


def orient(model, cfg):
    model.root.rotation_euler = tuple(math.radians(v) for v in cfg.get("rotate", (0, 0, 0)))
    model.root.location = cfg.get("at", (0, 0, 0))
