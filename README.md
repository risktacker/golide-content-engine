# GOLIDE Content Engine

The repository is being rebuilt as the **owned-distribution engine** for GOLIDE:

`create → schedule → publish → engage → measure`

The locked architecture is in [`docs/distribution-system-v1.md`](docs/distribution-system-v1.md).

## Rebuild rules

- Esiah's recorded voice only. **No ElevenLabs or cloned narration.**
- GitHub stores code only; it is not a media warehouse.
- Database records stay lightweight and store remote platform IDs, not media bytes.
- Media is temporary and will be deleted after publish confirmation.
- One final video render after the timeline is locked; no chains of scene/draft MP4 checkpoints.
- Social platforms sit behind replaceable provider adapters.
- AI providers are replaceable and the product does not depend on a ChatGPT conversation.

## Current rebuild phase

Phase 1 establishes the new distribution core:

`master content → platform variants → schedule → provider adapter → publish → remote content ID`

The first provider is an in-memory adapter used by CI, which means tests cannot accidentally post to a real social account.

The previous Python/FFmpeg/YouTube production implementation remains in the repository temporarily while the new system replaces it in tested stages. It is **legacy migration code**, not the target architecture.

## Development

Python 3.11+ remains supported during the migration.

```bash
python -m pip install -e '.[production]'
python -m unittest discover -s tests -v
```

The existing `golide` CLI and legacy production workflows remain available until their replacement phases are complete.
