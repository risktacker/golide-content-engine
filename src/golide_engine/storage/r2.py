from __future__ import annotations

import hashlib
import hmac
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class PreparedUpload:
    media_ref: str
    upload_url: str
    expires_at: datetime


class DeleteHttpClient(Protocol):
    def delete(self, url: str) -> None: ...


class UrlLibDeleteClient:
    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    def delete(self, url: str) -> None:
        request = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds):
            return


class R2TemporaryMediaStore:
    """Cloudflare R2 bridge using S3-compatible presigned URLs.

    Media bytes move browser -> R2 -> social platform. The application server
    only creates signatures and deletes confirmed/expired temporary objects.
    """

    def __init__(
        self,
        *,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        delete_http: DeleteHttpClient | None = None,
    ):
        self.account_id = account_id.strip()
        self.access_key_id = access_key_id.strip()
        self.secret_access_key = secret_access_key.strip()
        self.bucket = bucket.strip()
        self.delete_http = delete_http or UrlLibDeleteClient()
        if not all((self.account_id, self.access_key_id, self.secret_access_key, self.bucket)):
            raise ValueError("R2 account, access key, secret and bucket are required")

    @property
    def host(self) -> str:
        return f"{self.account_id}.r2.cloudflarestorage.com"

    def prepare_upload(
        self,
        *,
        filename: str,
        media_kind: str,
        upload_ttl_seconds: int = 900,
        retention_hours: int = 24,
        now: datetime | None = None,
    ) -> PreparedUpload:
        now = now or datetime.now(timezone.utc)
        safe_name = _safe_filename(filename)
        day = now.strftime("%Y/%m/%d")
        key = f"temp/{day}/{uuid4().hex}-{safe_name}"
        ref = f"r2://{key}"
        return PreparedUpload(
            media_ref=ref,
            upload_url=self._presign("PUT", key, upload_ttl_seconds, now=now),
            expires_at=now + timedelta(hours=retention_hours),
        )

    def resolve(self, media_ref: str, *, expires_seconds: int = 3600) -> str:
        key = self._key(media_ref)
        return self._presign("GET", key, expires_seconds)

    def upload_bytes(
        self,
        *,
        filename: str,
        media_kind: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        retention_hours: int = 24,
    ) -> PreparedUpload:
        prepared = self.prepare_upload(
            filename=filename,
            media_kind=media_kind,
            retention_hours=retention_hours,
        )
        request = urllib.request.Request(
            prepared.upload_url,
            data=data,
            method="PUT",
            headers={"Content-Type": content_type},
        )
        with urllib.request.urlopen(request, timeout=60):
            pass
        return prepared

    def delete(self, media_ref: str) -> None:
        key = self._key(media_ref)
        self.delete_http.delete(self._presign("DELETE", key, 900))

    def _key(self, media_ref: str) -> str:
        if not media_ref.startswith("r2://"):
            raise ValueError("R2 media reference must start with r2://")
        key = media_ref[5:].lstrip("/")
        if not key or ".." in key.split("/"):
            raise ValueError("invalid R2 media reference")
        return key

    def _presign(
        self,
        method: str,
        key: str,
        expires_seconds: int,
        *,
        now: datetime | None = None,
    ) -> str:
        if expires_seconds < 1 or expires_seconds > 604800:
            raise ValueError("presigned URL expiry must be between 1 second and 7 days")
        now = now or datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        scope = f"{date_stamp}/auto/s3/aws4_request"
        canonical_uri = "/" + "/".join(
            urllib.parse.quote(part, safe="-_.~") for part in [self.bucket, *key.split("/")]
        )
        params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key_id}/{scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires_seconds),
            "X-Amz-SignedHeaders": "host",
        }
        canonical_query = "&".join(
            f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}"
            for k, v in sorted(params.items())
        )
        canonical_headers = f"host:{self.host}\n"
        canonical_request = "\n".join([
            method.upper(),
            canonical_uri,
            canonical_query,
            canonical_headers,
            "host",
            "UNSIGNED-PAYLOAD",
        ])
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])
        signing_key = _signature_key(self.secret_access_key, date_stamp, "auto", "s3")
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return (
            f"https://{self.host}{canonical_uri}?{canonical_query}"
            f"&X-Amz-Signature={signature}"
        )


def r2_store_from_environment() -> R2TemporaryMediaStore | None:
    values = {
        "account_id": os.getenv("R2_ACCOUNT_ID", "").strip(),
        "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "").strip(),
        "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
        "bucket": os.getenv("R2_BUCKET", "").strip(),
    }
    if not any(values.values()):
        return None
    if not all(values.values()):
        raise RuntimeError(
            "R2 is partially configured; R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY and R2_BUCKET must all be set"
        )
    return R2TemporaryMediaStore(**values)


def _signature_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = hmac.new(("AWS4" + secret).encode(), date_stamp.encode(), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
    return hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()


def _safe_filename(filename: str) -> str:
    name = filename.strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
    return (name or "media.bin")[:120]
