from __future__ import annotations

import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from golide_engine.storage import Database
from golide_engine.storage.r2 import r2_store_from_environment
from golide_engine.web import StudioService


def run() -> int:
    store = r2_store_from_environment()
    if store is None:
        raise RuntimeError("R2 temporary storage is not configured")

    payload = b"GOLIDE Studio R2 smoke test\n"

    with tempfile.TemporaryDirectory() as tmp:
        database = Database(Path(tmp) / "golide.sqlite3")
        database.initialize()
        studio = StudioService(database, media_store=store)

        prepared = studio.prepare_media_upload({
            "filename": "studio-r2-smoke-test.txt",
            "media_kind": "render_asset",
        })

        registered = database.rows(
            "SELECT status, post_id FROM temporary_media WHERE object_key=?",
            (prepared["media_ref"],),
        )
        if not registered or registered[0]["status"] != "active":
            raise RuntimeError("Studio did not register temporary media")

        upload = urllib.request.Request(
            prepared["upload_url"],
            data=payload,
            method="PUT",
            headers={"Content-Type": "text/plain"},
        )
        with urllib.request.urlopen(upload, timeout=30) as response:
            if response.status not in {200, 201, 204}:
                raise RuntimeError(f"R2 upload returned HTTP {response.status}")

        read_url = store.resolve(prepared["media_ref"], expires_seconds=300)
        with urllib.request.urlopen(read_url, timeout=30) as response:
            downloaded = response.read()
            if response.status != 200:
                raise RuntimeError(f"R2 read returned HTTP {response.status}")

        if downloaded != payload:
            raise RuntimeError("R2 smoke test payload mismatch")

        scheduled = datetime.now(timezone.utc) + timedelta(hours=2)
        created = studio.create_post({
            "title": "R2 smoke test",
            "master_text": "Temporary integration verification",
            "scheduled_at": scheduled.isoformat(),
            "value_units": [
                "Temporary storage upload verification.",
                "Scheduled attachment retention verification.",
                "Temporary object cleanup verification.",
            ],
            "variants": [
                {
                    "platform": platform,
                    "body": "Temporary integration verification",
                    "media_ref": prepared["media_ref"],
                }
                for platform in ("instagram", "facebook", "linkedin", "x")
            ],
        })
        attached = database.rows(
            "SELECT post_id, expires_at FROM temporary_media WHERE object_key=?",
            (prepared["media_ref"],),
        )[0]
        if attached["post_id"] != created["id"]:
            raise RuntimeError("Studio did not attach temporary media to the post")
        if datetime.fromisoformat(attached["expires_at"]) < scheduled + timedelta(hours=24):
            raise RuntimeError("Studio did not extend scheduled-media retention")

        store.delete(prepared["media_ref"])

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

    print("Studio R2 smoke test passed: prepare -> upload -> attach -> read -> delete")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
