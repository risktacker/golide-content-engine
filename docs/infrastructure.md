# Infrastructure operations

## Non-negotiable production rule

This repository does not generate trial media. CI runs syntax and unit tests only.
Paid generation occurs only for a real release job containing both
`production_authorized: true` and `release.approved: true`. The production and
YouTube upload locks are separate.

## Repository layout

| Path | Responsibility |
|---|---|
| `src/golide_engine/providers/` | Replaceable OpenAI research, script, image, voice and caption adapters |
| `src/golide_engine/orchestration/` | Approved queue, stage checkpoints and complete production assembly |
| `src/golide_engine/youtube/` | OAuth, channel lock, private upload, scheduling and Analytics API |
| `src/golide_engine/storage/` | SQLite schema and transaction wrapper |
| `src/golide_engine/feedback/` | Parameter-level performance factors returned to concept scoring |
| `src/golide_engine/quality/` | Audio, video, safe-zone, thumbnail and spelling QA |
| `src/golide_engine/music/` | Licensed track selection and attribution ledger |
| `src/golide_engine/release/` | Checksummed release directory and ZIP |
| `production-queue/` | Approved, dated production jobs |

Thumbnail policy is separate from channel-banner framing. Thumbnails are normalized to
1280×720 and use the consistent unrealistic paper-cut Esiah avatar, one topic-specific
visual consequence and no words by default. Banner narrow-center safe-area rules do not
apply to thumbnail composition.

## Secure YouTube OAuth bootstrap

Use the infrastructure Google account to own the Google Cloud project, then authorize
the YouTube channel account during consent. The application never needs either Google
password.

1. Create a Google Cloud project and enable YouTube Data API v3 and YouTube Analytics API.
2. Configure an External OAuth consent screen and add `esiahsbusiness@gmail.com`
   as a test user while configuring it.
3. Before creating the final automation token, change the app publishing status to
   **In production**. A Testing refresh token expires after seven days. A personal,
   unverified production app can show Google's unverified-app warning; do not authorize
   it for anyone except the channel owner.
4. Create a Desktop OAuth client and download its JSON to
   `.secrets/youtube-client.json`.
5. Run `golide oauth-bootstrap .secrets/youtube-client.json` locally.
6. In the browser, select `esiahsbusiness@gmail.com` and approve the displayed scopes.
7. Run `golide youtube-verify`. It must return channel
   `UCqaXVBSBz7iQsRHOupKt-3w`; any other channel fails closed.
8. Base64-encode `.secrets/youtube-token.json` and store it as the private GitHub
   Actions secret `YOUTUBE_OAUTH_TOKEN_B64`. Never commit either OAuth file.

Requested scopes are limited to managing uploads plus reading analytics and monetary
analytics. The code has no channel-country update operation. The channel country stays
India and is explicitly outside this engine's configuration scope.

## GitHub secrets and variables

Secrets:

- `OPENAI_API_KEY`
- `YOUTUBE_OAUTH_TOKEN_B64`
- `GOLIDE_FAILURE_WEBHOOK` (optional)

Repository variables remain off until the OAuth check succeeds and a real approved job
is queued:

- `GOLIDE_ANALYTICS_ENABLED=true` enables the daily read-only collector.
- `GOLIDE_AUTOMATION_ENABLED=true` enables hourly checks for due approved jobs.

## Production job

Copy `examples/production-job.json` into `production-queue/`, replace every placeholder,
and set a generation time and future publishing time in UTC. Only after the concept,
budget and release are final should both approval flags become true.

The scheduler builds exactly one due job at a time. A successful job is renamed with
`.completed.json`; a failed stage remains checkpointed for a safe retry. Upload is
resumable, private first and idempotent by the video-plus-metadata fingerprint.

## Analytics and feedback

The daily job backfills the previous three complete days so delayed YouTube metrics are
updated. It stores views, engaged views, retention, engagement, subscriber change and
estimated revenue per video/day. Generation parameters remain joined to the uploaded
video ID. Feedback factors require at least three productions with the same parameter,
use shrinkage for small samples and can move a concept score by at most five points.

## Release package

Every successful release contains the video, 1280×720 thumbnail, upload metadata,
spoken captions, visual captions, claim/music source ledger, generation parameters,
QA report, cost summary and SHA-256 package manifest. Missing licensing, failed QA,
wrong channel identity or an exceeded cost ceiling blocks upload.
