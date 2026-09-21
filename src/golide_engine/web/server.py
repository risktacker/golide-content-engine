from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from golide_engine.storage import Database
from golide_engine.storage.r2 import r2_store_from_environment
from .service import StudioService

_AUTH_CACHE: dict[str, tuple[float, bool]] = {}
_AUTH_CACHE_SECONDS = 30


def _admin_from_cookie(cookie_header: str) -> bool:
    if not cookie_header:
        return False
    cache_key = hashlib.sha256(cookie_header.encode("utf-8")).hexdigest()
    cached = _AUTH_CACHE.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]

    session_url = os.getenv(
        "GOLIDE_AUTH_SESSION_URL",
        "https://golidee.com/api/auth/session",
    ).strip()
    request = urllib.request.Request(
        session_url,
        headers={
            "Accept": "application/json",
            "Cookie": cookie_header,
            "User-Agent": "GOLIDE-Content-Engine/1.0",
        },
    )
    allowed = False
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        allowed = bool(payload.get("user", {}).get("isAdmin"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        allowed = False

    _AUTH_CACHE[cache_key] = (time.time() + _AUTH_CACHE_SECONDS, allowed)
    return allowed


class StudioHandler(BaseHTTPRequestHandler):
    service: StudioService
    app_dir: Path

    def _json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        return _admin_from_cookie(self.headers.get("Cookie", ""))

    def _require_admin(self, path: str) -> bool:
        if self._authorized():
            return True

        if path.startswith("/api/"):
            self._json(401, {"error": "admin authentication required"})
            return False

        login = "https://golidee.com/login?returnTo=" + quote("/studio", safe="")
        self.send_response(302)
        self.send_header("Location", login)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return False

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not self._require_admin(parsed.path):
            return
        if parsed.path == "/api/health":
            return self._json(200, {"status": "ok"})
        if parsed.path == "/api/overview":
            return self._json(200, self.service.overview())
        if parsed.path == "/api/posts":
            status = parse_qs(parsed.query).get("status", [None])[0]
            return self._json(200, {"posts": self.service.posts(status)})
        if parsed.path == "/api/inbox":
            return self._json(200, {"threads": self.service.inbox_rows()})
        if parsed.path == "/api/connections":
            return self._json(200, {"connections": self.service.connection_rows()})
        if parsed.path == "/api/policy":
            return self._json(200, self.service.policy_snapshot())
        return self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self._require_admin(parsed.path):
            return
        if parsed.path == "/api/posts":
            try:
                created = self.service.create_post(self._read_json())
            except (ValueError, TypeError, KeyError) as exc:
                return self._json(400, {"error": str(exc)})
            return self._json(201, created)
        if parsed.path == "/api/media/prepare":
            try:
                prepared = self.service.prepare_media_upload(self._read_json())
            except RuntimeError as exc:
                return self._json(503, {"error": str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                return self._json(400, {"error": str(exc)})
            return self._json(201, prepared)
        if parsed.path == "/api/social-image/generate":
            try:
                generated = self.service.generate_social_image(self._read_json())
            except RuntimeError as exc:
                return self._json(503, {"error": str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                return self._json(400, {"error": str(exc)})
            return self._json(201, generated)
        return self._json(404, {"error": "not found"})

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (self.app_dir / relative).resolve()
        try:
            candidate.relative_to(self.app_dir.resolve())
        except ValueError:
            return self._json(403, {"error": "forbidden"})
        if not candidate.exists() or not candidate.is_file():
            candidate = self.app_dir / "index.html"
        suffix = candidate.suffix.lower()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(suffix, "application/octet-stream")
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store" if suffix == ".html" else "public, max-age=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def serve(
    *,
    database_path: str = "data/golide.sqlite3",
    app_dir: str = "app",
    host: str = "127.0.0.1",
    port: int = 8787,
) -> None:
    database = Database(database_path)
    database.initialize()
    media_store = r2_store_from_environment()
    handler = type(
        "ConfiguredStudioHandler",
        (StudioHandler,),
        {
            "service": StudioService(database, media_store=media_store),
            "app_dir": Path(app_dir).resolve(),
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"GOLIDE Content Engine: http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/golide.sqlite3")
    parser.add_argument("--app-dir", default="app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    serve(
        database_path=args.database,
        app_dir=args.app_dir,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
