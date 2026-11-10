# Route B example (trial, 2026-11-10)

Three.js render of a CAD object on the house grid stage: physical materials, reflections, soft shadows,
gold rim and bloom, slow camera push, measure lines and labels in the 3D scene. Not wired into the engine.

- `turbine_cad.py`: the stand-in build123d turbine (hand-written for the trial; production objects come from the CAD model call).
- `index.html`: the scene. Put the built STL files and `object.json` next to it.
- `run.js`: headless Chromium (Playwright) renders frames: `node run.js stills 0.5,2.5` or `node run.js video 11`,
  with `three@0.170.0` installed beside it. Then `ffmpeg -framerate 30 -i frames/f%04d.jpg out.mp4`.
