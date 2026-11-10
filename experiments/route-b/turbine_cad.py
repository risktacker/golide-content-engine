from build123d import *
import math


def blade(length):
    sections = []
    for i, f in enumerate((0.0, 0.25, 0.6, 1.0)):
        chord = 4.2 * (1 - 0.78 * f)
        thick = chord * (0.35 - 0.2 * f)
        twist = 18 * (1 - f)
        plane = Plane.XZ.offset(-(3 + f * length)).rotated((0, twist, 0))
        sections.append(plane * Ellipse(chord / 2, thick / 2))
    return loft(sections)


def build():
    with BuildPart() as tower:
        with BuildSketch(Plane.XY):
            Circle(2.2)
        with BuildSketch(Plane.XY.offset(80)):
            Circle(1.3)
        loft()
    with BuildPart() as nacelle:
        Box(12, 4.2, 4.2)
        fillet(nacelle.edges(), 1.2)
    nacelle_part = nacelle.part.moved(Location((-3, 0, 82.5)))
    hub = Solid.make_cone(2.0, 0.4, 3.6, Plane((3, 0, 82.5), z_dir=(1, 0, 0)))
    blades = []
    for k in range(3):
        b = blade(55).rotate(Axis.Y, 0).moved(Location((4, 0, 82.5)) * Rotation(k * 120, 0, 0))
        blades.append(b)
    return {"tower": tower.part, "nacelle": nacelle_part, "hub": hub,
            "blade_1": blades[0], "blade_2": blades[1], "blade_3": blades[2]}
