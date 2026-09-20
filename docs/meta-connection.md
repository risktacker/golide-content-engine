# Meta connection — Instagram + Facebook

The Content Engine treats Instagram and Facebook as independent Meta
connections.

## Instagram — preferred route: Instagram Login

Instagram Professional accounts (Business or Creator) connect directly through
Instagram Login. This route does **not** require a Facebook Page to be linked.

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
```

The Instagram account ID is resolved from the token at runtime. A manually
copied `GOLIDE_INSTAGRAM_USER_ID` is not required for the direct Instagram
Login path.

## Facebook Page — separate connection

Facebook Page publishing remains independent and uses:

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
META_USER_ACCESS_TOKEN=<temporary Page discovery token, if needed>
META_PAGE_ACCESS_TOKEN=<Page publishing token>
GOLIDE_FACEBOOK_PAGE_ID=<Page id>
```

Required Page permissions:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`

## Safety lock

Real publishing stays disabled until explicitly enabled:

```text
GOLIDE_ENABLE_SOCIAL_PUBLISH=1
```

Leave this unset while account connections are being validated.
