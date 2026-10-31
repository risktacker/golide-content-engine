# Explainer prototypes (2026-10-31 milestone: real product + real architecture)

Hand-built references for the iPhone Duo explainer, kept for the next step (3D motion).

- `real.py` -> `real.png`: the real product (book-style foldable, 9:41 lock screen), drawn in code.
  `real_plate.py` exports it cut out (`duo_product.png` + `.plate.json`), which the engine shows
  whole as a real-product plate (`vector.illustrate.load_plate`).
- `arch.py` -> `arch.png`: exploded screen layers and the hinge parts (the engine's `layers` figure).
- `closeup.py` -> `closeup.png`: the hinge end view, screen looping, bar, gears, springs, cable
  (the engine's `fold` figure).
- `demo.py` (+ `*_anim.py`): the first animated sample; `engine_short.py`: the same script through
  the engine renderer (background, sets, pen reveal, captions).

Run from a scratch folder; paths inside point at the session scratchpad and need adjusting.
Next (from Monday 2 Nov): 3D motion for products and architecture.
