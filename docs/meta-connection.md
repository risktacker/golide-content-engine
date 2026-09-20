# Meta connection — Instagram + Facebook

The Content Engine uses one Meta integration for Facebook Page publishing and
Instagram Professional publishing.

## Required account shape

- A Facebook Page managed by the GOLIDE account.
- An Instagram Professional account (Business or Creator) linked to that Page
  when using the Facebook Login route.
- A Meta app with the required Page/Instagram permissions approved for the
  environment in which the app will run.

## Required permissions

For the current adapter:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`
- `instagram_basic`
- `instagram_content_publish`

Comment/inbox permissions are added when that adapter is enabled; they are not
required merely to prove publishing.

## Environment contract

Secrets are not written into SQLite or committed to GitHub.

```text
GOLIDE_META_API_VERSION=<Graph API version configured for the app>
META_USER_ACCESS_TOKEN=<temporary token used only for account discovery>
META_PAGE_ACCESS_TOKEN=<Page token used by the publishing adapters>
GOLIDE_FACEBOOK_PAGE_ID=<Page id>
GOLIDE_INSTAGRAM_USER_ID=<Instagram professional account id>

# Safety lock. Leave unset until the account test is complete.
GOLIDE_ENABLE_SOCIAL_PUBLISH=1
```

## Discovery

With only the user token and API version configured:

```bash
golide meta-discover
```

The command prints Page IDs, Page names, Instagram professional account IDs and
Page tasks. It deliberately does not print access tokens.

## Diagnostics

```bash
golide social-status
```

This reports whether required settings exist without displaying their values.

## Publishing

```bash
golide social-publish-due
```

Real publishing is refused unless `GOLIDE_ENABLE_SOCIAL_PUBLISH=1`.

Instagram:
- single-image content creates a media container, waits until Meta reports it
  finished, then publishes the container;
- video uses the Reels container path;
- media must be an HTTPS URL from temporary object storage.

Facebook:
- text posts use the Page feed;
- images use the Page photos edge;
- Facebook video/Reels publishing is intentionally handled by the dedicated
  video adapter because its upload lifecycle differs from text/photo publishing.

No published URL is guessed. The remote content ID is persisted immediately;
permalinks can be fetched in the later analytics/sync layer.
