from __future__ import annotations

from dataclasses import dataclass

from .models import Annotation, Motion


BRAND_COLORS = {
    "warm-ivory": "F5F1E8",
    "deep-navy": "111B36",
    "neon-blue": "00C8FF",
    "golide-gold": "F4B942",
    "danger-red": "E04B4B",
}


@dataclass(frozen=True)
class Transition:
    name: str
    duration: float


def transition_for(motion: Motion, fps: int) -> Transition:
    if motion.transition == "cut":
        return Transition("fadefast", 1 / fps)
    if motion.transition == "paper-wipe":
        return Transition("wipeleft", 0.22)
    if motion.transition == "match-cut":
        return Transition("fadefast", 0.12)
    return Transition("circleopen", 0.24)


def _progress(frames: int, easing: str) -> str:
    linear = f"min(1,on/{max(1, frames - 1)})"
    if easing == "linear":
        return linear
    if easing == "ease-in":
        return f"({linear})*({linear})"
    if easing == "ease-out":
        return f"1-(1-({linear}))*(1-({linear}))"
    return f"({linear})*({linear})*(3-2*({linear}))"


def _strength(intensity: str) -> float:
    return {"subtle": 0.035, "medium": 0.075, "strong": 0.12}[intensity]


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def annotation_filter(annotation: Annotation, width: int, height: int) -> str | None:
    if annotation.kind == "none":
        return None
    color = BRAND_COLORS[annotation.color_token]
    font_size = {
        "keyword": round(min(width, height) * 0.065),
        "number": round(min(width, height) * 0.11),
        "label": round(min(width, height) * 0.045),
        "callout": round(min(width, height) * 0.04),
    }[annotation.kind]
    positions = {
        "top": ("(w-text_w)/2", "h*0.14"),
        "center": ("(w-text_w)/2", "(h-text_h)/2"),
        "bottom": ("(w-text_w)/2", "h*0.72"),
        "left": ("w*0.10", "(h-text_h)/2"),
        "right": ("w*0.90-text_w", "(h-text_h)/2"),
    }
    x, y = positions[annotation.position]
    end = annotation.start_offset + annotation.duration
    return (
        "drawtext="
        f"text='{_escape_text(annotation.text)}':"
        "font='DejaVu Sans':fontcolor=#" + color + ":"
        f"fontsize={font_size}:borderw=3:bordercolor=#111B36:"
        "box=1:boxcolor=#111B36@0.72:boxborderw=18:"
        f"x={x}:y={y}:enable='between(t,{annotation.start_offset:.3f},{end:.3f})'"
    )


def scene_filter(
    motion: Motion,
    annotation: Annotation,
    width: int,
    height: int,
    fps: int,
    duration: float,
    *,
    still_image: bool = True,
) -> str:
    frames = max(1, round(duration * fps))
    p = _progress(frames, motion.easing)
    strength = _strength(motion.intensity)
    base_scale = 1.015 if motion.type == "hold" else 1.0
    end_scale = base_scale + strength

    if motion.type == "pull-out":
        zoom = f"{1 + strength:.5f}-{strength:.5f}*({p})"
    elif motion.type in {"pan-left", "pan-right", "reframe"}:
        zoom = f"{1 + max(0.06, strength):.5f}"
    elif motion.type == "hold":
        zoom = f"{base_scale:.5f}+0.006*sin(on/11)"
    else:
        zoom = f"{base_scale:.5f}+{end_scale - base_scale:.5f}*({p})"

    center_x = "(iw-iw/zoom)/2"
    center_y = "(ih-ih/zoom)/2"
    if motion.type == "pan-left":
        x = f"(iw-iw/zoom)*(1-({p}))"
        y = center_y
    elif motion.type == "pan-right":
        x = f"(iw-iw/zoom)*({p})"
        y = center_y
    elif motion.type == "reframe":
        x = f"(iw-iw/zoom)*(0.18+0.64*({p}))"
        y = f"(ih-ih/zoom)*(0.62-0.24*({p}))"
    else:
        x, y = center_x, center_y

    filters = [
        f"scale={round(width * 1.18)}:{round(height * 1.18)}:force_original_aspect_ratio=increase",
        f"crop={round(width * 1.18)}:{round(height * 1.18)}",
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames if still_image else 1}:s={width}x{height}:fps={fps}",
    ]
    if motion.type == "layer-reveal":
        filters.append("fade=t=in:st=0:d=0.18")
    overlay = annotation_filter(annotation, width, height)
    if overlay:
        filters.append(overlay)
    filters.extend([f"fps={fps}", "format=yuv420p"])
    return ",".join(filters)
