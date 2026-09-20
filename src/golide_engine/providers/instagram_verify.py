from __future__ import annotations

import os

from .meta import discover_instagram_identity


def main() -> int:
    api_version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
    token = os.getenv("INSTAGRAM_USER_ACCESS_TOKEN", "").strip()

    missing = [
        name
        for name, value in (
            ("GOLIDE_META_API_VERSION", api_version),
            ("INSTAGRAM_USER_ACCESS_TOKEN", token),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing Instagram configuration: " + ", ".join(missing))

    identity = discover_instagram_identity(
        api_version=api_version,
        instagram_access_token=token,
    )

    print(f"Instagram connection verified: @{identity.username or 'unknown'} ({identity.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
