# Temporary media transport

The Content Engine does not keep a permanent media library.

## Data path

```text
browser
  -> request short-lived upload URL from Content Engine
  -> PUT file directly to Cloudflare R2
  -> Content Engine stores only r2:// logical reference
  -> at publish time create a fresh signed HTTPS GET URL
  -> social platform reads the temporary object
  -> platform returns a remote content ID
  -> after every selected platform confirms, delete the R2 object
```

The application server never proxies image, audio, or video bytes.

## Required R2 settings

```text
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
```

These are runtime secrets. They must not be committed to GitHub or written into
the SQLite database.

## Browser uploads and CORS

The R2 bucket must allow `PUT` from the deployed Studio origin. The presigned
URL is short-lived and is scoped to a single generated temporary object key.

The Studio calls:

```text
POST /api/media/prepare
{ "filename": "post.mp4", "media_kind": "video" }
```

and receives:

```json
{
  "media_ref": "r2://temp/...",
  "upload_url": "https://...signed...",
  "expires_at": "..."
}
```

The browser then uploads the file directly to `upload_url`.

## Retention rules

- Default unassigned temporary media expiry: 24 hours.
- When temporary media is attached to a scheduled post, expiry is extended to
  at least 24 hours after the scheduled publish time.
- A partial publish never triggers deletion.
- A fully confirmed publish marks referenced media ready for immediate cleanup.
- Expired abandoned media is removed by the cleanup job.
- Database rows remain as lightweight audit state; media bytes do not.

## Commands

Publish due content and clean newly-confirmed temporary media:

```bash
golide social-publish-due
```

Clean confirmed or expired temporary media without publishing:

```bash
golide social-media-cleanup
```

## Storage invariant

GitHub stores source code, tests, configuration and small reusable assets only.
Rendered images, user voice recordings and final videos are temporary objects,
not repository artifacts or resumable GitHub caches.
