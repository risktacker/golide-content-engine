# GOLIDE Content Engine

Independent, lightweight production engine for evidence-led YouTube Shorts and
16:9 videos up to five minutes. The first release is intentionally not a SaaS:
it stores jobs on disk, renders with FFmpeg, and keeps providers replaceable.

## MVP workflow

1. Research and approve a topic.
2. Save a structured project manifest.
3. Add generated images and/or licensed stock clips per scene.
4. Add narration and optional music.
5. Render a 9:16 Short or 16:9 video.
6. Review locally before upload.

Uploads remain manual until rendering quality is proven.

## Requirements

- Python 3.11+
- FFmpeg and ffprobe on `PATH`

No Python packages are required for the first renderer.

## Quick start

```bash
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

## Roadmap

- Phase A: deterministic renderer and project schema
- Phase B: research, scripting, image, stock, voice and thumbnail providers
- Phase C: YouTube OAuth upload and analytics collector
- Phase D: performance feedback and experiment scoring

