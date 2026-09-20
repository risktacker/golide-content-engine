from __future__ import annotations

import os
import urllib.error
import urllib.request

from .r2 import r2_store_from_environment


def run() -> int:
    store = r2_store_from_environment()
    if store is None:
        raise RuntimeError("R2 temporary storage is not configured")

    payload = b"GOLIDE R2 smoke test\n"
    prepared = store.prepare_upload(
        filename="r2-smoke-test.txt",
        media_kind="render_asset",
        upload_ttl_seconds=300,
        retention_hours=1,
    )

    upload = urllib.request.Request(
        prepared.upload_url,
        data=payload,
        method="PUT",
        headers={"Content-Type": "text/plain"},
    )
    with urllib.request.urlopen(upload, timeout=30) as response:
        if response.status not in {200, 201, 204}:
            raise RuntimeError(f"R2 upload returned HTTP {response.status}")

    read_url = store.resolve(prepared.media_ref, expires_seconds=300)
    with urllib.request.urlopen(read_url, timeout=30) as response:
        downloaded = response.read()
        if response.status != 200:
            raise RuntimeError(f"R2 read returned HTTP {response.status}")

    if downloaded != payload:
        raise RuntimeError("R2 smoke test payload mismatch")

    store.delete(prepared.media_ref)

    deleted = False
    try:
        with urllib.request.urlopen(read_url, timeout=30):
            pass
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404}:
            deleted = True
        else:
            raise

    if not deleted:
        raise RuntimeError("R2 object remained readable after delete")

    print("R2 smoke test passed: upload -> read -> delete")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
