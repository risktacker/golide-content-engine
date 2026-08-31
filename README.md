# GOLIDE Content Engine

Independent, lightweight production engine for evidence-led YouTube Shorts and
16:9 videos up to five minutes. The first release is intentionally not a SaaS:
it stores jobs on disk, renders with FFmpeg, and keeps providers replaceable.

## Pipeline

`research → concept scoring → script → ElevenLabs narration/timing → editorial beats → motion/asset plan → assets → FFmpeg composition → thumbnail → automated QA → private upload → schedule → analytics → feedback`

Shorts and 16:9 videos use different scoring weights. Both must pass an evidence
gate, a cost ceiling, and an approved production job before any paid generation.
Every upload is private first and is scheduled only after automatic QA passes.

## Locked production policy

`config/production-policy.json` is the production source of truth created from
the first Short review. Future videos require a circular hook, a mature and
highly engaging explainer delivery, licensed background music with voice ducking,
and two simultaneous caption systems: scene-level visual labels plus smaller
spoken captions in the bottom safe zone. Explanations default to centered paper
subjects with intentional negative space; the consistent GOLIDE avatar appears
when emotion or human stakes improve the explanation.

The cosmic-ray proof is preserved for manual scheduling on 7 September 2026.
The first video uploaded through the automated pipeline will be the first
weekly long-form production.

## Requirements

- Python 3.11+
- FFmpeg and ffprobe on `PATH`
- Production extras: `pip install -e '.[production]'`

## Quick start

```bash
python -m golide_engine score examples/concept-short.json
python -m golide_engine plan examples/concept-long.json
cp examples/short.json projects/first-short.json
python -m golide_engine validate projects/first-short.json
python -m golide_engine render projects/first-short.json
```

Place scene media at the paths listed in the manifest. The rendered video is
written to `build/<project-id>/video.mp4`.

## Safety and cost controls

- `max_cost_usd` is mandatory in every manifest.
- Provider calls will be refused when their estimate exceeds that ceiling.
- AI video generation is excluded from the MVP.
- Prefer reusable paper-cut assets, generated stills, layered inserts and deterministic FFmpeg motion.
- Paid generation is locked unless the job is approved and `GOLIDE_ENABLE_PAID_PRODUCTION=1`.
- Uploading has a separate `GOLIDE_ENABLE_YOUTUBE_UPLOAD=1` lock.
- The expected channel is pinned to `UCqaXVBSBz7iQsRHOupKt-3w`.
- Unknown or zero provider pricing blocks the complete production before its first API call.
- Each API request is recorded against its production and checked against the cost ceiling.
- No workflow triggered by a code push generates media or spends API credits.

See [the evidence-led content strategy](docs/research/strategy.md) for the channel
findings, benchmark patterns, format specifications, first proof pair, and cost target.
See [the YouTube publishing standard](docs/youtube-publishing.md) for titles,
descriptions, chapters, tags, disclosure, language, location and upload QA.

## Infrastructure status

- Beat-driven FFmpeg Motion Composer with push/pull/pan/reframe/reveal camera grammar
- Independently timed foreground/detail/inset layers, GOLIDE-token annotations and varied transitions
- Procedural owned SFX, licensed-music ducking and dual captions
- GPT-5.6 Sol high-reasoning research, script and structured-output adapter
- GPT Image 2 asset and thumbnail adapters, including avatar reference edits
- Approved cloned ElevenLabs narrator with native alignment as the master timeline
- 27,000-character monthly narration guard and per-production character accounting
- YouTube installed-app OAuth, channel identity check, resumable private upload and scheduling
- Daily analytics storage, parameter-level feedback and concept-score adjustments
- Loudness, frame, safe-zone, editorial timing, motion repetition, SFX density, thumbnail-size and spelling QA
- Retry checkpoints, webhook failure events, cost ledger and checksummed release ZIP
- GitHub workflows for CI, daily analytics and approved due productions

The read-only analytics workflow is active. Paid production remains gated by an approved
job, an approved voice profile, explicit production locks and repository configuration. See [Infrastructure operations](docs/infrastructure.md).
