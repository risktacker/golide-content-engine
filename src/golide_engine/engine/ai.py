from __future__ import annotations

from typing import Protocol

from .scripts import ScriptBrief, ScriptPackage


class ScriptAIProvider(Protocol):
    """Replaceable provider boundary for script generation."""

    def generate_script(self, brief: ScriptBrief) -> ScriptPackage:
        ...
