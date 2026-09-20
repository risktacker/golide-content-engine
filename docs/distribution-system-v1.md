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
