from __future__ import annotations

import json
from pathlib import Path


class SocialImageProfile:
    def __init__(self, path: str | Path = "config/social-image-profile.json"):
        self.path = Path(path)
        self.raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not self.raw.get("locked"):
            raise RuntimeError("social image profile is not locked")

    @property
    def model(self) -> str:
        return self.raw["generation"]["model"]

    @property
    def quality(self) -> str:
        return self.raw["generation"]["quality"]

    GLOW_COLORS = {
        "gold": "warm soft gold",
        "cyan": "cool soft cyan",
        "white": "clean soft white",
    }

    def build_prompt(
        self,
        *,
        concept: str,
        glow_color: str = "gold",
        hook: str = "",
        context: str = "",
    ) -> str:
        """Locked GOLIDE Black still prompt (innertune reference, 2026-10-04).

        The image model only draws the picture. The hook is typeset afterwards
        by code (see engine.typeset), so the prompt forbids any text.
        """
        concept = " ".join(concept.split())
        if not concept:
            raise ValueError("a visual concept is required")
        glow = self.GLOW_COLORS.get(glow_color, self.GLOW_COLORS["gold"])
        return (
            "Vertical 2:3 artwork. Pure black deep-space background (#0B0B0E) with a very faint, "
            "sparse starfield and a subtle dark vignette. "
            f"SUBJECT: {concept} "
            "Render the subject as luminous fine-line illustration or a cinematic, softly lit real "
            "object, alone in the black space, centered in the upper two thirds of the frame. "
            f"Exactly one element of the subject glows with a {glow} light; everything else is "
            "rendered in thin, calm white or grey lines. High contrast, minimal, calm, premium, "
            "instantly readable in one second. One subject only, no clutter, no busy background, "
            "no collage. If a hand or person appears, they are dark-skinned/Black. "
            "Keep the bottom third of the image completely empty and dark: no objects, no light. "
            "Keep the subject inside the central square so it survives 4:5 and 1:1 crops. "
            "ABSOLUTELY NO text, letters, words, numbers, captions, labels, logos, watermarks, "
            "signatures, user-interface elements or borders anywhere in the image."
        )

    @staticmethod
    def adapt(
        master: Path,
        meta_output: Path,
        square_output: Path,
        *,
        hook: str = "",
        emphasis: str = "",
    ) -> None:
        try:
            from golide_engine.engine.typeset import compose_post
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Pillow is required for social image adaptation; install production dependencies"
            ) from exc
        compose_post(master, hook, emphasis, meta_output, (1080, 1350), centering=(0.5, 0.42))
        compose_post(master, hook, emphasis, square_output, (1080, 1080), centering=(0.5, 0.36))
