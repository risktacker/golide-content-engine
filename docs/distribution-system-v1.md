# GOLIDE Distribution System — locked build contract

This document records the implementation contract for the September 2026 rebuild.

## Two engines

- **Partner Engine** — borrowed distribution at `https://marketplace.golidee.com/partners/`.
- **Content Engine** — owned distribution in `risktacker/golide-content-engine`.

Both point toward the GOLIDE product catalogue, conversion, and attributable revenue.

## Non-negotiable build rules

1. Esiah's recorded voice is the only narration source. No ElevenLabs and no cloned voice.
2. GitHub stores code, configuration, schemas, tests, and small reusable assets — not rendered media checkpoints.
3. Media is temporary. A successful publish must return a platform content ID before cleanup can remove the temporary object.
4. Videos produce one final render after the timeline is locked. Intermediate scene MP4 chains are not part of the new design.
5. AI is provider-replaceable. Prompts and structured outputs belong to the engine, not to one chat session or model vendor.
6. Database rows store lightweight records and remote IDs, never image/audio/video bytes.
7. Platform-specific behavior lives behind provider adapters so platform churn does not rewrite the content engine.

## Build order

1. Content Engine core: create, schedule, publish.
2. Connections and inbox.
3. Temporary storage and confirmation-driven cleanup.
4. Video research/script engine plus the locked reference-video editing profile.
5. Partner discovery and scoring.
6. Outreach and communication bridge.
7. Deals and analytics.

## Phase 1 contract

The first core normalizes one master item into platform variants, schedules it, publishes it through replaceable provider adapters, records remote content IDs, and makes failures explicit. The first adapter is in-memory only so CI cannot accidentally contact a real account. Real Instagram, Facebook, LinkedIn, X and YouTube connectors are added only after their account connection is configured.


## Locked content operating system

The production cadence and routing are now machine-readable in:

- `config/content-routing.json`
- `config/content-calendar.json`
- `config/social-image-profile.json`
- `config/video-profile.json`
- `config/automation-schedule.json`

### Platform routing

- Instagram: static posts and short videos.
- Facebook: static posts and short videos.
- LinkedIn: static posts only.
- X: static posts only.
- YouTube: Shorts and long-form video only. No static-post workflow.
- Pinterest: outside native engine automation for now; reconnect and derive manually from Instagram.

### Locked weekly cadence

- 2 core static posts every day: 14 per week.
- Every core post receives platform-specific copy for Instagram, Facebook, LinkedIn and X.
- 4 short videos per week: Monday, Wednesday, Friday and Sunday.
- Shorts route to Instagram, Facebook and YouTube.
- 2 long videos per week: Tuesday and Saturday.
- Long videos route to YouTube only.

Clock times are operational defaults and may later be optimized from analytics. Cadence and routing do not change without an explicit policy revision.

### Static post structure

Each core post uses 3 to 4 related value units. The second or third unit can create a deliberate next-step gap that redirects to the most relevant GOLIDE product. The bridge must be useful and contextual rather than an artificial sales interruption. Where a platform supports a natural thread or follow-up-comment presentation, units can be rendered that way; otherwise they remain clearly separated parts of the post body.

### Static image identity

Static feed images do not reuse the video frame language by default. They use the locked `GOLIDE Social Post Editorial` profile: premium realistic conceptual/editorial still-life, believable photography, sparse composition, one strong metaphor, restrained cyan light, subtle gold when useful, short white hook text, small GOLIDE branding, and dark-skinned/Black hands whenever hands are intentionally featured. Dark navy or black is a strong option, not a mandatory background.

Instagram and Facebook use 4:5 as the primary feed composition. LinkedIn and X use a 1:1 adaptation of the same concept.

