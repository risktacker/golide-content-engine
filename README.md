# GOLIDE Content Engine

Independent, lightweight production engine for evidence-led YouTube Shorts and
16:9 videos up to five minutes. The first release is intentionally not a SaaS:
it stores jobs on disk, renders with FFmpeg, and keeps providers replaceable.

## Pipeline

`research → concept scoring → script → storyboard → assets → voice → captions → render → thumbnail → human QA`

Shorts and 16:9 videos use different scoring weights. Both must pass an evidence
gate, a cost ceiling, and manual approval before production or publishing.

Uploads remain manual until rendering quality is proven.

## Requirements

- Python 3.11+
- FFmpeg and ffprobe on `PATH`

No Python packages are required for the first renderer.

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

## Cost controls

- `max_cost_usd` is mandatory in every manifest.
- Provider calls will be refused when their estimate exceeds that ceiling.
- AI video generation is excluded from the MVP.
- Prefer Pexels footage, generated stills, and FFmpeg motion effects.
- Uploading is never automatic unless `publish.approved` is explicitly true.

See [the evidence-led content strategy](docs/research/strategy.md) for the channel
findings, benchmark patterns, format specifications, first proof pair, and cost target.

## Roadmap

- Phase A: deterministic renderer and project schema
- Phase B: provider adapters for research, scripting, assets, voice and thumbnails
- Phase C: YouTube OAuth upload and analytics collector
- Phase D: performance feedback and experiment scoring
