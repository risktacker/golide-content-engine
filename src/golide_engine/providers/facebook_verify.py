from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error


def main() -> int:
    api_version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
    page_token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("GOLIDE_FACEBOOK_PAGE_ID", "").strip()

    missing = [
        name for name, value in (
            ("GOLIDE_META_API_VERSION", api_version),
            ("META_PAGE_ACCESS_TOKEN", page_token),
            ("GOLIDE_FACEBOOK_PAGE_ID", page_id),
        ) if not value
    ]
    if missing:
        raise RuntimeError("missing Facebook configuration: " + ", ".join(missing))

    params = urllib.parse.urlencode({
        "fields": "id,name",
        "access_token": page_token,
    })
    url = f"https://graph.facebook.com/{api_version}/{page_id}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Meta Graph API returned HTTP {exc.code}: {body}") from None

    resolved_id = str(payload.get("id", ""))
    if resolved_id != page_id:
        raise RuntimeError(
            f"Facebook Page id mismatch: token resolved {resolved_id}, expected configured id"
        )

    print(f"Facebook Page connection verified: {payload.get('name', 'unknown')} ({resolved_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
