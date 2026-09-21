from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageOps


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

    def build_prompt(self, *, hook: str, concept: str, context: str = "") -> str:
        hook = hook.strip()
        concept = concept.strip()
        if not hook or not concept:
            raise ValueError("hook and visual concept are required")
        if "—" in hook or "–" in hook:
            raise ValueError("hook must not use extended dash typography")
        if len(hook) > 90:
            raise ValueError("hook is too long for the locked static-post image style")
        return (
            "Create one premium realistic conceptual editorial still-life for GOLIDE. "
            "The scene may use dark navy or black, but do not force darkness: use believable "
            "real-photo colors and a real environment when that makes the concept stronger. "
            "Use restrained electric-cyan light as an identity cue and subtle metallic or gold "
            "only when useful. Keep the composition sparse with one strong physical or visual "
            "metaphor and one dominant focal idea. No clutter, no generic stock-photo look, "
            "no busy collage, no excessive glow, no large logo. If hands are intentionally "
            "visible, they must be dark-skinned/Black hands. Do not invent random people. "
            "Place a short clean white hook in the upper-left with generous safe margins; a thin "
            "cyan underline is optional. Place a small understated GOLIDE wordmark at bottom-right. "
            "Keep all essential visual information inside a central square-safe area so the same "
            "paid master can be adapted to 4:5 and 1:1 without breaking the metaphor or hook. "
            f'HOOK TEXT: "{hook}". VISUAL METAPHOR: {concept}. '
            f"CONTENT CONTEXT: {context.strip() or 'Use only the supplied metaphor and hook.'}"
        )

    @staticmethod
    def adapt(master: Path, meta_output: Path, square_output: Path) -> None:
        with Image.open(master) as image:
            image = image.convert("RGB")
            meta = ImageOps.fit(
                image, (1080, 1350), method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.43),
            )
            square = ImageOps.fit(
                image, (1080, 1080), method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.38),
            )
            meta_output.parent.mkdir(parents=True, exist_ok=True)
            square_output.parent.mkdir(parents=True, exist_ok=True)
            meta.save(meta_output, "JPEG", quality=94, optimize=True)
            square.save(square_output, "JPEG", quality=94, optimize=True)
