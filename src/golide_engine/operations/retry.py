from __future__ import annotations

import random
import ssl
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def is_transient_error(exc: Exception) -> bool:
    status = (
        getattr(exc, "status_code", None)
        or getattr(exc, "code", None)
        or getattr(getattr(exc, "resp", None), "status", None)
    )
    return status in {408, 409, 429, 500, 502, 503, 504} or isinstance(
        exc, (TimeoutError, ConnectionError, ConnectionResetError, BrokenPipeError, ssl.SSLError)
    )


def with_retry(
    operation: Callable[[], T], *, attempts: int = 4, base_delay: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == attempts or not is_transient_error(exc):
                raise
            sleeper(base_delay * (2 ** (attempt - 1)) + random.uniform(0, base_delay / 4))
    raise RuntimeError("unreachable")
