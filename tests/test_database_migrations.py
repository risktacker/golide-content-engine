import sqlite3
import tempfile
import unittest
from pathlib import Path

from golide_engine.storage.database import Database


class DatabaseMigrationTests(unittest.TestCase):
    def test_legacy_uploads_table_migrates_before_index_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "legacy.sqlite3"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE productions (
                    production_id TEXT PRIMARY KEY,
                    format TEXT NOT NULL,
                    concept_family TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approved INTEGER NOT NULL DEFAULT 0,
                    scheduled_at TEXT,
                    youtube_video_id TEXT UNIQUE,
                    parameters_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE uploads (
                    production_id TEXT PRIMARY KEY REFERENCES productions(production_id),
                    youtube_video_id TEXT UNIQUE,
                    privacy_status TEXT NOT NULL,
                    scheduled_at TEXT,
                    upload_status TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL UNIQUE,
                    updated_at TEXT NOT NULL
                );
                """
            )
            connection.commit()
            connection.close()

            Database(db_path).initialize()

            connection = sqlite3.connect(db_path)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(uploads)")}
            indexes = {row[1] for row in connection.execute("PRAGMA index_list(uploads)")}
            connection.close()

            self.assertIn("uploaded_at", columns)
            self.assertIn("media_purged_at", columns)
            self.assertIn("idx_upload_uploaded_at", indexes)


if __name__ == "__main__":
    unittest.main()
