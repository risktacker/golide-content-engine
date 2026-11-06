# Handover: World 3D (Blender path), 2026-11-06

Repo `risktacker/golide-content-engine`, branch **`world3d-space-kit`** (commit `9d09c5c`).
Not merged. Off by default. Live production is untouched.

## Read this first: there are now two 3D engines
- **On `main`, live:** `src/golide_engine/vector/motion3d.py`. Built in another session on 2026-11-06.
  Code-drawn rasterizer (numba), objects from box/cyl/sphere/cone written by the storyboard,
  moves on the spoken word, house grid stage. Rules are in `main`'s `CLAUDE.md`.
- **On this branch, not live:** `world3d/` + `src/golide_engine/explain3d/`. Real Blender (Cycles),
  real lighting and materials, worlds (space with Earth, studio grid), researched blueprints.

They overlap. Decide before more work: keep main's engine as the default and use this branch as the
"realistic" toggle in Studio (the owner's original idea: switch visuals per video), or drop one.
The branch merges cleanly into `main` today (checked), but `main` is 47 commits ahead and also edits
`production.py`, `vector/render.py` and `production-scheduler.yml`, so rebase and rerun tests first.

## What the owner wants (standing)
- An engine that can explain anything (machines, chips, weapons at explainer level, biology) in GOLIDE's
  own 3D look, from published structure. Not one-off shots, not hand-made artwork.
- Reusable worlds and parts, like a game engine. Deep, well-structured, connected files, no blockages.
- Free sources only (NCBI, RCSB PDB, Smithsonian CC0, NASA). Nothing that needs a licence or payment.
  Own code first; hosted or AI 3D only if our route fails. Higgsfield is dropped.
- No time estimates. No realistic faces for now. State costs before spending. Previews before visual pushes.
- Tell him plainly when a stopping point is reached.

## Built on this branch
| Stage | File | State |
|---|---|---|
| Kit layers | `world3d/kit/*` (registry, worlds, parts, objects, materials, lights, cameras, actions, effects, labels) | Works |
| Catalog | `world3d/catalog.json` | 10 builders, 17 materials, 2 worlds, 4 moves. What the model may use |
| Blueprint | `explain3d/blueprint.py` | Research to checked blueprint, retries with errors, saves per run |
| Director | `explain3d/director.py` | Script + word timing to shots; actions land on spoken words |
| Render | `explain3d/stage.py`, `world3d/render_shot.py`, `world3d/post.py` | Renders; a failed shot is skipped |
| Composer | `vector/clips.py`, hook in `vector/render.py` | 3D clips laid under captions |
| Production hook | `orchestration/production.py` stage `world3d-v1` | Runs only if `config/world3d.json` enabled |
| CI | `.github/workflows/world3d-check.yml`, `world3d/smoke_test.py` | Passed on GitHub 2026-11-05 (2m10s) |
| Tests | `tests/test_explain3d.py` | 9 new; 415 total passed on the branch |

## Not done
1. Real Luna run on one script (about $0.03 tokens + web search per new subject). Never run yet.
2. Blueprints made in a run are not kept between videos, so a repeated subject is paid again.
   Fix: store them in R2 or commit to `world3d/blueprints/`.
3. Shots render one after another. `--frames lo-hi` exists for splitting across jobs; not wired.
4. Studio toggle (Illustrated / 3D) not built.
5. Look: objects plain, framing needs tuning. Do this after the path is proven.
6. More worlds (ground, sea, city, inside a machine, inside the body) and builders (pipes, wires,
   boards, tracks, wings, organs from free sources).

## Run it
```bash
python3 -m venv .venv-blender && .venv-blender/bin/pip install bpy numpy pillow   # Blender needs Python 3.13
pip install -e '.[production,video]'
PYTHONPATH=src python world3d/smoke_test.py --blender-python .venv-blender/bin/python --out out
.venv-blender/bin/python world3d/render_shot.py world3d/shots/space_hubble.json --out out/h --quality draft --stills 48
```
Speed seen on 2 CPU cores: about 7 s per 720p studio frame, 14 s per 540p space frame.
Earth maps download once to `~/.cache/golide-world3d` (NASA Blue Marble via turban/webgl-earth).

## Notes
- A stop hook kept claiming this branch had unpushed commits. It was false every time; local and GitHub matched.
- Hubble blueprint source: NASA SM3B media guide, section 5. Estimated parts are listed in its `simplified` field.
