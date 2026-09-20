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

## Instagram — direct Instagram Login

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
INSTAGRAM_USER_ACCESS_TOKEN=<Instagram Login user token>
GOLIDE_INSTAGRAM_USER_ID=<Instagram professional account id>
```

This is the preferred Instagram path. It does not require a Facebook Page link.

Required scopes:
- `instagram_business_basic`
- `instagram_business_content_publish`

## Facebook Page

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
META_USER_ACCESS_TOKEN=<discovery only>
META_PAGE_ACCESS_TOKEN=<Page publishing token>
GOLIDE_FACEBOOK_PAGE_ID=<Page id>
```

Facebook is connected separately from Instagram.

## LinkedIn

```text
LINKEDIN_ACCESS_TOKEN=<member or organization-authorized access token>
GOLIDE_LINKEDIN_AUTHOR_URN=<urn:li:person:... or urn:li:organization:...>
GOLIDE_LINKEDIN_VERSION=<YYYYMM>
```

The adapter supports text, image and MP4 video publishing.

## X

```text
X_USER_ACCESS_TOKEN=<user-context token with post-write/media permissions>
```

The adapter supports text, image and chunked video publishing.

## Diagnostics

```bash
golide social-status
```

The command reports only whether settings exist. It never prints token values.

## Scheduled publishing

```bash
golide social-publish-due
```

The job loads configured providers, resolves temporary media for publishing,
stores remote content IDs, and deletes media only after the complete selected
platform publish succeeds.
