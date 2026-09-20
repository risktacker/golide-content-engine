"""Replaceable providers for production and social distribution.

Legacy production providers load lazily so the lightweight distribution core
does not import media/AI dependencies until they are explicitly requested.
"""

from .base import PublishRequest, PublishResult, SocialProvider
from .memory import MemoryProvider

__all__ = [
    "FacebookPageProvider",
    "InstagramProvider",
    "LinkedInProvider",
    "MemoryProvider",
    "ProviderRegistry",
    "PublishRequest",
    "PublishResult",
    "SocialProvider",
    "XProvider",
]


def __getattr__(name: str):
    if name == "ProviderRegistry":
        from .registry import ProviderRegistry
        return ProviderRegistry
    if name in {"FacebookPageProvider", "InstagramProvider"}:
        from .meta import FacebookPageProvider, InstagramProvider
        return {"FacebookPageProvider": FacebookPageProvider, "InstagramProvider": InstagramProvider}[name]
    if name == "LinkedInProvider":
        from .linkedin import LinkedInProvider
        return LinkedInProvider
    if name == "XProvider":
        from .x import XProvider
        return XProvider
    raise AttributeError(name)
