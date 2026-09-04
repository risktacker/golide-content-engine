from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any


class VisualIdentity:
    def __init__(self, config_path: str | Path):
        self.path = Path(config_path)
        self.config: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        if self.config.get("locked") is not True:
            raise RuntimeError("G$LIDE visual identity must remain locked for production")

    @property
    def avatar(self) -> dict[str, Any]:
        return dict(self.config["avatar"])

    @property
    def repository_root(self) -> Path:
        # visual-identity.json lives under <repo>/config/.
        return self.path.resolve().parent.parent

    def requests_avatar(self, prompt: str) -> bool:
        value = prompt.lower()
        markers = [str(item).lower() for item in self.avatar.get("reference_markers", [])]
        return any(marker in value for marker in markers)

    def canonical_avatar_reference(self) -> Path:
        avatar = self.avatar
        source_rel = avatar.get("canonical_reference_b64")
        expected_sha = avatar.get("canonical_reference_sha256")
        if not source_rel or not expected_sha:
            raise RuntimeError("canonical G$LIDE avatar reference is not configured")

        source = self.repository_root / str(source_rel)
        if not source.is_file():
            raise RuntimeError(f"canonical G$LIDE avatar source is missing: {source}")

        target = self.repository_root / "generated" / "brand" / "golide-canonical-avatar-v1.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha:
            try:
                raw = source.read_text(encoding="ascii").strip()
                raw = raw.replace("\\r\\n", "").replace("\\n", "").replace("\\r", "").replace("\\t", "")
                if raw.startswith('"') and raw.endswith('"'):
                    raw = raw[1:-1]
                if raw.lower().startswith("data:") and "base64," in raw.lower():
                    raw = raw.split(",", 1)[1]
                encoded = "".join(raw.split())
                alphabet = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
                encoded = "".join(ch for ch in encoded if ch in alphabet)

                # A previous repository transport concatenated encoded material after a
                # padded JPEG payload. Recover only a segment whose decoded bytes match
                # the already-locked canonical SHA-256. This cannot accept a substitute.
                candidates = [encoded]
                candidates.extend(re.findall(r"[A-Za-z0-9+/]+={1,2}", encoded))
                candidates.extend(re.findall(r"[A-Za-z0-9+/]{128,}", encoded))

                payload = None
                seen: set[str] = set()
                for candidate in candidates:
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    padded = candidate + ("=" * ((-len(candidate)) % 4))
                    try:
                        decoded = base64.b64decode(padded, validate=True)
                    except Exception:
                        continue
                    if hashlib.sha256(decoded).hexdigest() == expected_sha:
                        payload = decoded
                        break
                if payload is None:
                    raise ValueError("no encoded segment matches locked canonical checksum")
            except Exception as exc:
                raise RuntimeError("canonical G$LIDE avatar reference is not valid base64") from exc

            actual = hashlib.sha256(payload).hexdigest()
            if actual != expected_sha:
                raise RuntimeError(
                    f"canonical G$LIDE avatar checksum mismatch: expected {expected_sha}, got {actual}"
                )
            target.write_bytes(payload)

        return target

    def prompt_guard(self) -> str:
        avatar = self.avatar
        required = "; ".join(avatar["required_traits"])
        forbidden = "; ".join(avatar["forbidden_traits"])
        palette = ", ".join(self.config["palette"])
        non_avatar_rule = avatar.get(
            "non_avatar_rule",
            "Do not invent a host, presenter or substitute avatar in topic visuals.",
        )
        return (
            "LOCKED G$LIDE VISUAL IDENTITY. "
            f"Palette: {palette}. "
            "Maintain a premium layered paper-cut/technical-explainer aesthetic. "
            "If the image contains the G$LIDE Esiah avatar or any representation of Esiah, "
            f"the canonical avatar direction is mandatory: {avatar['canonical_direction']} "
            f"Required avatar traits: {required}. "
            f"Forbidden avatar traits: {forbidden}. "
            f"Thumbnail rule: {avatar['thumbnail_rule']} "
            f"In-video rule: {avatar['in_video_rule']} "
            f"Non-avatar rule: {non_avatar_rule} "
            "Do not reinterpret the avatar as a cartoon, mascot, anime figure or animated-film character."
        )

    def apply(self, prompt: str) -> str:
        return self.prompt_guard() + "\n\nSCENE REQUEST:\n" + prompt.strip()
