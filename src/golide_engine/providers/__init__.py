"""Replaceable providers for production and social distribution.

Legacy production providers load lazily so the lightweight distribution core
does not import media/AI dependencies until they are explicitly requested.
"""

from .base import PublishRequest, PublishResult, SocialProvider
from .memory import MemoryProvider

__all__ = [
    "FacebookPageProvider",
    "InstagramProvider",
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
    if name in {"FacebookPageProvider", "InstagramProvider"}:
        from .meta import FacebookPageProvider, InstagramProvider
        return {"FacebookPageProvider": FacebookPageProvider, "InstagramProvider": InstagramProvider}[name]
    raise AttributeError(name)
