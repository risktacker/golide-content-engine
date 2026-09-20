# Social connection environment contract

Real publishing is disabled unless:

```text
GOLIDE_ENABLE_SOCIAL_PUBLISH=1
```

Leave that unset while connecting and validating accounts.

## Temporary media

Media is uploaded directly from the Studio browser to temporary Cloudflare R2
storage. See `temporary-media.md`.

```text
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
```

The database stores only `r2://...` references. At publish time the engine
creates a fresh signed HTTPS URL for the platform adapter. Once all selected
platforms confirm with remote content IDs, the temporary object is deleted.

## Meta

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
META_USER_ACCESS_TOKEN=<discovery only>
META_PAGE_ACCESS_TOKEN=<Page publishing token>
GOLIDE_FACEBOOK_PAGE_ID=<Page id>
GOLIDE_INSTAGRAM_USER_ID=<Instagram professional account id>
```

Instagram and Facebook share the Meta connection. See `meta-connection.md`.
Instagram handles image containers and Reels. Facebook currently handles Page
text and photo posts; its dedicated video path is added with the video publishing
adapter.

## LinkedIn

```text
LINKEDIN_ACCESS_TOKEN=<member or organization-authorized access token>
GOLIDE_LINKEDIN_AUTHOR_URN=<urn:li:person:... or urn:li:organization:...>
GOLIDE_LINKEDIN_VERSION=<YYYYMM>
```

The adapter supports:
- text posts;
- image initialization/upload followed by a post using the returned image URN;
- MP4 video initialization, byte-range multipart upload, ETag finalization, then
  a post using the returned video URN.

## X

```text
X_USER_ACCESS_TOKEN=<user-context token with post-write/media permissions>
```

The adapter supports:
- text posts;
- image upload then Post creation with the returned media ID;
- chunked video initialize/append/finalize, processing-status polling, then Post
  creation with the returned media ID.

## Diagnostics

```bash
golide social-status
```

The command reports only whether settings exist. It never prints token values.

## Scheduled publishing

```bash
golide social-publish-due
```

The job loads fully configured providers, resolves temporary media only for the
duration of the publish, stores platform content IDs, and deletes media only
after the complete selected-platform publish has succeeded.
