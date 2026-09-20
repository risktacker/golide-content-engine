# Social connection environment contract

Real publishing is disabled unless:

```text
GOLIDE_ENABLE_SOCIAL_PUBLISH=1
```

Leave that unset while connecting and validating accounts.

## Meta

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
META_USER_ACCESS_TOKEN=<discovery only>
META_PAGE_ACCESS_TOKEN=<Page publishing token>
GOLIDE_FACEBOOK_PAGE_ID=<Page id>
GOLIDE_INSTAGRAM_USER_ID=<Instagram professional account id>
```

Instagram and Facebook share the Meta connection. See `meta-connection.md`.

## LinkedIn

```text
LINKEDIN_ACCESS_TOKEN=<member or organization-authorized access token>
GOLIDE_LINKEDIN_AUTHOR_URN=<urn:li:person:... or urn:li:organization:...>
GOLIDE_LINKEDIN_VERSION=<YYYYMM>
```

The current adapter supports text-only organic posts through the Posts API.
Media remains deliberately blocked until the LinkedIn image/video upload adapter
returns a real media URN.

For member posting the authorization needs the member social write permission.
Organization posting requires the corresponding organization social write access
and an account with the required organization role.

## X

```text
X_USER_ACCESS_TOKEN=<user-context token with post-write permission>
```

The current adapter creates text Posts through the X API v2. Media remains
deliberately blocked until the media upload path is implemented.

## Diagnostics

```bash
golide social-status
```

The command reports only whether settings exist. It never prints token values.

## Scheduled publishing

```bash
golide social-publish-due
```

The job loads only fully configured providers, publishes due variants, stores the
remote content IDs, and marks temporary media for cleanup only after every
platform variant for that item has succeeded.
