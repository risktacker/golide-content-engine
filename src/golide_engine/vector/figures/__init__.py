"""Exact figures: the math and physics layer (owner direction 2026-10-16).

Pictures from the image model are sketches: angles, lengths and curves are
guessed. When a scene's words teach exact maths, physics or engineering, the
storyboard gives the scene a ``figure`` in a one-line spec instead::

    right_triangle: a=3; b=4; angle=yes

Each kind lives with its family (maths, mechanics, optics, waves, heat,
relativity). Every number on screen is computed here, drawn in the house style
and saved as a PNG plus a sidecar of exact pen strokes and labels that the
renderer animates (see ``vector.illustrate.load_figure``). No image model,
no cost, and the geometry is true.
"""

from __future__ import annotations

from pathlib import Path

from . import heat, maths, mechanics, optics, relativity, waves
from .core import FigureError, parse_figure, save, sidecar_path

BUILDERS = {
    # maths
    "vectors": maths.vectors, "right_triangle": maths.right_triangle, "function": maths.function,
    "unit_circle": maths.unit_circle,
    # mechanics and engineering
    "projectile": mechanics.projectile, "beam": mechanics.beam, "forces": mechanics.forces,
    "motion": mechanics.motion, "newton": mechanics.newton, "incline": mechanics.incline,
    # optics and light
    "lens": optics.lens, "reflection": optics.reflection, "refraction": optics.refraction,
    "prism": optics.prism, "wave": waves.wave, "spectrum": waves.spectrum,
    # thermodynamics
    "pv": heat.pv, "heat_engine": heat.heat_engine,
    # relativity
    "light_clock": relativity.light_clock, "lorentz": relativity.lorentz,
}
KINDS = tuple(BUILDERS)

# One example per kind: the storyboard's menu (see illustrate.scene_plan_instructions).
EXAMPLES = {
    "vectors": "vectors: a=3,1; b=1,2; sum=yes          (names=u,v to rename; length=yes)",
    "right_triangle": "right_triangle: a=3; b=4; angle=yes     (formula=yes adds a² + b² = c²; letters=yes)",
    "function": "function: f=x^2; x=-2,2; tangent=1      (or area=0,3.14 for the area under the curve)",
    "unit_circle": "unit_circle: angle=30; wave=yes         (sin and cos with the sine wave)",
    "projectile": "projectile: speed=20; angle=45          (m/s and degrees; range and peak computed)",
    "beam": "beam: length=6; load=10; at=2           (metres and kN; support reactions computed)",
    "forces": "forces: 20@0; 15@120                    (newtons at degrees; net force computed)",
    "motion": "motion: points=0,0 4,20 10,20 12,0      (velocity-time; accelerations and distance computed)",
    "newton": "newton: force=10; mass=2; friction=4    (F = ma; acceleration computed)",
    "incline": "incline: angle=30; mass=5              (weight split along and into the slope)",
    "lens": "lens: focal=10; object=25; type=convex  (ray diagram; image place, size, real/virtual computed)",
    "reflection": "reflection: angle=40                    (angle in = angle out)",
    "refraction": "refraction: n1=1; n2=1.5; angle=40      (Snell's law; total internal reflection when it happens)",
    "prism": "prism: spread=8                         (white light into colours, traced per colour)",
    "wave": "wave: wavelength=2; amplitude=1; frequency=5   (speed = f × λ when frequency is given)",
    "spectrum": "spectrum: highlight=infrared            (radio to gamma on a true scale, visible band opened up)",
    "pv": "pv: process=isothermal; p1=200; v1=1; v2=3   (kPa and L; isobaric, isochoric, adiabatic too; work computed)",
    "heat_engine": "heat_engine: hot=500; cold=300; heat=1000   (kelvin and joules; best efficiency computed)",
    "light_clock": "light_clock: speed=0.8                  (fraction of light speed; time stretch computed)",
    "lorentz": "lorentz: speed=0.8                      (γ against speed, the speed marked)",
}


def render_figure(spec: str, target: Path, size: tuple[int, int]) -> Path:
    """Draw the figure named by ``spec`` to ``target`` (PNG + sidecar). Raises FigureError."""
    kind, params, items = parse_figure(spec)
    builder = BUILDERS.get(kind)
    if builder is None:
        raise FigureError(f"unknown figure kind {kind!r}")
    try:
        canvas = builder(size, params, items)
    except FigureError:
        raise
    except Exception as exc:  # a bad number or expression must never crash a video
        raise FigureError(f"{kind}: {exc}") from exc
    return save(canvas, target)


def check_figure(spec: str) -> str:
    """'' when the spec draws, else the reason it cannot."""
    import tempfile

    try:
        with tempfile.TemporaryDirectory() as tmp:
            render_figure(spec, Path(tmp) / "f.png", (512, 512))
        return ""
    except FigureError as exc:
        return str(exc)


__all__ = ["BUILDERS", "EXAMPLES", "KINDS", "FigureError", "check_figure", "parse_figure", "render_figure",
           "sidecar_path"]
