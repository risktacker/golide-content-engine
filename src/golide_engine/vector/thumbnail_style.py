"""YouTube thumbnails in the static-post look, in several colours (owner direction 2026-10-18).

"Our static posts have the best image generation of Studio ever... use that now
with multiple colours per thumbnail and adding simple text like we do." So the
thumbnail art follows the static-post prompt (luminous fine line or a softly lit
real object alone on deep-space black with a faint starfield, calm white and grey
lines) but glows in two or three colours chosen by meaning, and the typeset words
take the same colours.
"""

from __future__ import annotations

from .illustrate import ACCENTS

# How each accent is named to the image model, and what it means.
GLOW_WORDS = {
    "gold": "warm soft gold",
    "rose": "soft rose red",
    "teal": "cool electric teal",
    "ivory": "clean warm ivory white",
    "copper": "glowing copper orange",
}
DEFAULT = ("gold", "teal")


def thumbnail_colors(cover: dict, scenes: list[dict]) -> list[str]:
    """Two or three accent names: the storyboard's choice, else the cover scene's
    accent plus the next most used accent in the video."""
    chosen = [c for c in (cover.get("colors") or []) if c in ACCENTS]
    if len(chosen) >= 2:
        return chosen[:3]
    counts: dict[str, int] = {}
    first = ""
    for scene in scenes:
        accent = str(scene.get("accent") or "")
        if accent in ACCENTS:
            counts[accent] = counts.get(accent, 0) + 1
            if scene.get("id") == cover.get("scene"):
                first = accent
    ranked = [a for a, _ in sorted(counts.items(), key=lambda kv: -kv[1])]
    out = [c for c in [*chosen, first, *ranked, *DEFAULT] if c]
    unique: list[str] = []
    for c in out:
        if c not in unique:
            unique.append(c)
    return unique[:2]


def thumbnail_prompt(title: str, moment: str, colors: list[str]) -> str:
    subject = moment.strip() or f"one iconic object that stands for the story behind: {title}"
    names = [GLOW_WORDS.get(c, c) for c in colors] or [GLOW_WORDS["gold"]]
    glow = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return (
        "16:9 YouTube thumbnail artwork. Pure black deep-space background (#0B0B0E) with a very faint, "
        "sparse starfield and a subtle dark vignette. "
        f"ONE hero object, nothing else: {subject}. "
        "Render the subject as luminous fine-line illustration or a cinematic, softly lit real object, "
        "alone in the black space, big and bold in the right 55 percent of the frame, slightly angled "
        "toward the camera, crisp and readable at phone-thumbnail size. "
        f"Its key parts glow, each in its own colour: {glow}; everything else is rendered in thin, calm "
        "white or grey lines. High contrast, minimal, premium, instantly readable in one second. "
        "One subject only, no clutter, no busy background, no collage. Keep the left 40 percent clean, "
        "dark and empty for a title. No people, no faces, no hands, no avatars, no characters, "
        "no paper-cut, low-poly or origami figures. "
        "ABSOLUTELY NO text, letters, words, numbers, captions, labels, logos, watermarks, signatures, "
        f"user-interface elements or borders anywhere in the image. Video title for context only: {title}"
    )


def palette_rgb(colors: list[str]) -> list[tuple[int, int, int]]:
    return [ACCENTS[c] for c in colors if c in ACCENTS] or [ACCENTS["gold"]]
