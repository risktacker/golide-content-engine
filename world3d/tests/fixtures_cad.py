"""A blueprint as the writer would return it, used to test the real CAD path end to end."""

GEARBOX_CODE = '''
from build123d import *
import math


def gear(teeth, module, width):
    r_tip, r_root = module * (teeth + 2) / 2, module * (teeth - 2.5) / 2
    pts = []
    for i in range(teeth):
        for u, r in ((0.0, r_root), (0.22, r_root), (0.36, r_tip), (0.64, r_tip), (0.78, r_root)):
            a = 2 * math.pi * (i + u) / teeth
            pts.append((r * math.cos(a), r * math.sin(a)))
    with BuildPart() as g:
        with BuildSketch(Plane.XZ):
            Polygon(*pts)
            Circle(module * 2.2, mode=Mode.SUBTRACT)
        extrude(amount=width, both=True)
    return g.part


def build():
    big = gear(36, 0.004, 0.012).moved(Location((0, 0, 0.09)))
    small = gear(14, 0.004, 0.012).moved(Location((0.1, 0, 0.09)))
    with BuildPart() as case:
        Box(0.26, 0.06, 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
        fillet(case.edges().filter_by(Axis.Z), 0.006)
    shaft = Cylinder(0.008, 0.1, rotation=(90, 0, 0)).moved(Location((0, 0, 0.09)))
    return {"case": case.part.moved(Location((0.05, 0, 0))), "drive_gear": big, "pinion": small, "shaft": shaft}
'''

GEARBOX = {
    "name": "Two-stage gear set", "sources": ["https://example.org/gears"], "simplified": ["test object"],
    "code": GEARBOX_CODE,
    "parts": [
        {"id": "case", "label": "Case", "material": "metal_dark", "explode": [0, 0, 0]},
        {"id": "drive_gear", "label": "Drive gear", "material": "steel", "explode": [0, 0, 0.06]},
        {"id": "pinion", "label": "Pinion", "material": "copper", "explode": [0.04, 0, 0.06]},
        {"id": "shaft", "label": "Shaft", "material": "steel", "explode": [0, -0.08, 0.06]},
    ],
}
