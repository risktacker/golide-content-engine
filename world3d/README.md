# GOLIDE World 3D

Compiles a shot list into realistic 3D video with code only. No paid API and no licensed assets.
It is separate from the production engine until it is connected on purpose.

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

`src/golide_engine/explain3d/` is the planning side and needs no Blender:

1. `director.py` reads the script and voice timing and picks the shots.
2. `blueprint.py` turns research into a checked blueprint, saved so a subject is paid for once.
3. `director.py` compiles each shot, landing every action on a spoken word.
4. `stage.py` renders the shots. A failed shot is skipped and the video stays illustrated.
5. `vector/clips.py` lays the shots into the video, under the captions.

`config/world3d.json` turns the path on. It is off by default.
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
