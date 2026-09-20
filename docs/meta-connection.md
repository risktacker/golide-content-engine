# Meta connection — Instagram + Facebook

The Content Engine now treats Instagram and Facebook as independent Meta
connections.

## Instagram — preferred route: Instagram Login

Instagram Professional accounts (Business or Creator) connect directly through
Instagram Login. This route does **not** require a Facebook Page to be linked to
the Instagram account.

Required Instagram Login permissions:

- `instagram_business_basic`
- `instagram_business_content_publish`

Future inbox/comment work can additionally request:

- `instagram_business_manage_messages`
- `instagram_business_manage_comments`

Environment contract:

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
INSTAGRAM_USER_ACCESS_TOKEN=<Instagram Login user token>
GOLIDE_INSTAGRAM_USER_ID=<Instagram professional account id>
```

The engine uses `graph.instagram.com` for this direct Instagram path.

## Facebook Page — separate connection

Facebook Page publishing remains independent and uses:

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
META_USER_ACCESS_TOKEN=<temporary Page discovery token, if needed>
META_PAGE_ACCESS_TOKEN=<Page publishing token>
GOLIDE_FACEBOOK_PAGE_ID=<Page id>
```

Required Page permissions for the current publisher:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`

A Facebook Page is therefore not a prerequisite for the Instagram connection.

## Safety lock

Real publishing stays disabled until explicitly enabled:

```text
GOLIDE_ENABLE_SOCIAL_PUBLISH=1
```

Leave this unset while account connections are being validated.

## Diagnostics

```bash
golide social-status
```

The diagnostics report only whether credentials are configured. They never
display token values.

## Publishing

Instagram:
- image or Reel media is read from the temporary HTTPS R2 URL;
- a media container is created;
- processing is polled until finished;
- the container is published;
- the platform content ID is persisted.

Facebook:
- text posts use the Page feed;
- images use the Page photos edge;
- Facebook video/Reels remain a separate lifecycle.

Temporary media is deleted only after all selected platforms confirm publishing.
