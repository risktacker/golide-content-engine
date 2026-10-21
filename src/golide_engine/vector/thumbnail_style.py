"""YouTube thumbnails in the static-post look (owner direction 2026-10-18 and 2026-10-20).

"Look at this image... even if you can't be hooked, like how? This is the type I was
talking about for thumbs too." What makes the posts work, and what every thumbnail
now does:

* ONE subject: an object or a visual metaphor of the story's tension, chosen by the
  topic (a key with glowing teeth for leaked keys, a scale weighing a chip against
  coal, a cracked padlock with a glowing keyhole). Understood in one second.
* ONE element glows, in the story's meaning colour (not always blue), with premium
  lighting: a soft gradient halo of that colour fading out behind the subject, rim
  light on its edges and a faint spill below. Everything else is calm white or grey
  line on deep-space black.
* The subject fills the right of the frame; the left stays dark for one to three
  huge words (2026-10-21: "simple 1 to 3 words of catch and curiosity, not caption
  text"), the punch word in the glow colour. The bottom-right corner, where YouTube
  prints the duration, never carries text.
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
    subject = moment.strip() or f"one object or visual metaphor that captures the tension of the story: {title}"
    names = [GLOW_WORDS.get(c, c) for c in colors] or [GLOW_WORDS["gold"]]
    glow, rim = names[0], (names[1] if len(names) > 1 else names[0])
    return (
        "16:9 YouTube thumbnail artwork in a premium editorial poster style. Pure black deep-space "
        "background (#0B0B0E) with a very faint, sparse starfield. "
        f"ONE hero subject, nothing else: {subject}. "
        "Render it as luminous fine-line illustration or a cinematic, softly lit real object, alone in "
        "the black space, large, filling the right 55 percent of the frame top to bottom, slightly "
        "angled toward the camera, crisp and readable at phone-thumbnail size. "
        f"Exactly ONE key element of it glows bright {glow} (a neon-like inner light); everything else is "
        "drawn in thin, calm white and grey lines. "
        f"Premium lighting: a soft {glow} gradient halo fades outward behind the subject like an outer "
        f"glow, a subtle {rim} rim light traces its edges, and a faint pool of the same light spills "
        "beneath it. The glow colours are clean and saturated, never muddy; the black stays deep. "
        "High contrast, minimal, instantly readable in one second. One subject only: no clutter, no "
        "collage, no busy background. Keep the left 42 percent of the frame dark and empty for big title "
        "words. "
        "No faces, no full people, no avatars, no characters, no paper-cut, low-poly or origami figures; "
        "a single dark-skinned hand may appear only if the metaphor needs it. "
        "ABSOLUTELY NO text, letters, words, numbers, captions, labels, logos, watermarks, signatures, "
        f"user-interface elements or borders anywhere in the image. Video title for context only: {title}"
    )


def palette_rgb(colors: list[str]) -> list[tuple[int, int, int]]:
    return [ACCENTS[c] for c in colors if c in ACCENTS] or [ACCENTS["gold"]]
