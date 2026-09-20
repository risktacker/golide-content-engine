"""Replaceable providers for production and social distribution.

The legacy production registry is loaded lazily so the lightweight distribution
core does not import OpenAI/media dependencies unless that registry is actually
requested.
"""

from .base import PublishRequest, PublishResult, SocialProvider
from .memory import MemoryProvider

__all__ = [
    "MemoryProvider",
    "ProviderRegistry",
    "PublishRequest",
    "PublishResult",
    "SocialProvider",
]


def __getattr__(name: str):
    if name == "ProviderRegistry":
        from .registry import ProviderRegistry

        return ProviderRegistry
    raise AttributeError(name)
