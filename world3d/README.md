# GOLIDE World 3D

Compiles a shot list into realistic 3D video with code only. No paid API and no licensed assets.
It is a separate system from the production engine and its simple 3D (`src/golide_engine/vector/motion3d.py`).
Everything lives in this folder. Nothing in `src/` imports it and it imports nothing from `src/`.
It will connect through one marked hand-off (Studio picks 3D, the engine calls in here, gets clips back). Not built yet.

## How it fits together

| Layer | File | Job |
|---|---|---|
| Worlds | `kit/worlds.py` | Complete places that stay fixed. `space` has Earth, clouds, air and stars. |
| Blueprints | `blueprints/*.json` | Researched facts about a real object: parts, sizes, order, sources, and what was simplified. |
| Parts | `kit/parts.py` | Generic builders (barrel, bay ring, disc, solar wing, dish) driven by blueprint numbers. |
| Objects | `kit/objects.py` | Turns a blueprint into a 3D object made of named parts. |
| Materials | `kit/materials.py` | The look of every surface, defined once. |
| Lights | `kit/lights.py` | Light rigs. |
| Cameras | `kit/cameras.py` | Camera moves. |
| Actions | `kit/actions.py` | Explode, drift, glow. |
| Effects | `kit/effects.py` | Signal beam. |
| Labels | `kit/labels.py`, `post.py` | Text is drawn on finished frames, so changing a word needs no new render. |
| Shot list | `shots/*.json` | The one format that connects every layer. |

A new world, part, action or effect is one function with a registry decorator. A shot that
names something missing stops at once and lists what exists.

## The whole path

`explain3d/` is the planning side and needs no Blender:

1. `director.py` reads the script and voice timing and picks the shots.
2. `blueprint.py` turns research into a checked blueprint, saved so a subject is paid for once.
3. `director.py` compiles each shot, landing every action on a spoken word.
4. `stage.py` renders the shots. A failed shot is skipped and the video stays illustrated.
5. `explain3d/clips.py` holds the finished shots on the voice's clock, ready for the hand-off.

`config.json` holds shot limits and quality. `enabled` stays false until the hand-off exists.
Tests: `python -m pytest -q world3d/tests`.
`python world3d/smoke_test.py` proves the path on real Blender with no paid calls.

## Run one shot by hand

```bash
pip install bpy numpy pillow
python render_shot.py shots/space_hubble.json --out out --quality video
python post.py out
ffmpeg -framerate 24 -i out/final/f%05d.png -c:v libx264 -pix_fmt yuv420p out.mp4
```

Finished frames are kept, so a stopped run resumes. `--frames 0-143` splits a shot across
parallel jobs. Earth maps download once into `~/.cache/golide-world3d`; media is not stored in git.
