"""Generic part builders. Each takes plain numbers from a blueprint and returns meshes.
Axis convention: every part is built along +X from x=0, so blueprints just stack them."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials as mats
from .registry import parts


def _object(name, bm, material, smooth=True, bevel=0.0):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        ob.modifiers.new("split", "EDGE_SPLIT").split_angle = math.radians(32)
    if bevel:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width, b.segments, b.limit_method = bevel, 2, "ANGLE"
        b.angle_limit = math.radians(40)
    me.materials.append(material)
    return ob


def _tube(bm, r0, r1, x0, x1, segs=96, cap0=False, cap1=False, sides=None):
    """Tube along X from radius r0 to r1. `sides` makes it a flat-faced polygon barrel."""
    n = sides or segs
    ring0, ring1 = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        y, z = math.cos(a), math.sin(a)
        ring0.append(bm.verts.new((x0, r0 * y, r0 * z)))
        ring1.append(bm.verts.new((x1, r1 * y, r1 * z)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
    if cap0:
        bm.faces.new(list(reversed(ring0)))
    if cap1:
        bm.faces.new(ring1)


def _box(bm, center, size, matrix=None):
    m = Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)) @ Matrix.Scale(1, 4)
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=(matrix or Matrix()) @ m)
    return r


@parts.add("barrel")
def barrel(p, material):
    """Cylinder skin with outer reinforcing rings and optional handrails."""
    L, r = p["length"], p["diameter"] / 2
    bm = bmesh.new()
    _tube(bm, r, r, 0, L, cap0=p.get("cap", False), cap1=p.get("cap", False))
    skin = _object("skin", bm, material)
    obs = [skin]
    bm = bmesh.new()
    n = p.get("rings", 0)
    for i in range(n):
        x = L * (i + 0.5) / n if n > 1 else L / 2
        _tube(bm, r + 0.035, r + 0.035, x - 0.03, x + 0.03)
        _tube(bm, r, r + 0.035, x - 0.03, x - 0.03)
        _tube(bm, r + 0.035, r, x + 0.03, x + 0.03)
    if n:
        obs.append(_object("rings", bm, mats.get("panel_grey")))
    rails = p.get("rails", 0)
    if rails:
        obs.append(_rails(L, r, rails))
    return obs


def _rails(L, r, count):
    bm = bmesh.new()
    for i in range(count):
        a = 2 * math.pi * (i + 0.5) / count
        rot = Matrix.Rotation(a, 4, "X")
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.022, radius2=0.022, depth=L * 0.8,
                              matrix=rot @ Matrix.Translation((L / 2, 0, r + 0.11)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
        for k in range(5):
            x = L * (0.14 + 0.18 * k)
            bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.016, radius2=0.016, depth=0.12,
                                  matrix=rot @ Matrix.Translation((x, 0, r + 0.055)))
    return _object("rails", bm, mats.get("rail_yellow"))


@parts.add("bay_ring")
def bay_ring(p, material):
    """Flat-sided ring of equipment bays, with a raised door on every side."""
    L, r, n = p["length"], p["diameter"] / 2, p["bays"]
    bm = bmesh.new()
    _tube(bm, r, r, 0, L, sides=n, cap0=True, cap1=True)
    body = _object("body", bm, material, smooth=False)
    bm = bmesh.new()
    apothem = r * math.cos(math.pi / n)
    w = 2 * r * math.sin(math.pi / n) * 0.82
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        rot = Matrix.Rotation(a, 4, "X")
        _box(bm, (L / 2, 0, apothem + 0.02), (L * 0.84, w, 0.05), rot)
    doors = _object("bay_doors", bm, mats.get("panel_grey"), smooth=False, bevel=0.012)
    return [body, doors]


@parts.add("disc")
def disc(p, material):
    """A flat or dished disc, used for mirrors and bulkheads."""
    r = p["diameter"] / 2
    t = p.get("thickness", 0.1)
    hole = p.get("hole", 0) / 2
    bm = bmesh.new()
    _tube(bm, r, r, 0, t, cap0=not hole, cap1=not hole)
    if hole:
        _tube(bm, hole, r, 0, 0)
        _tube(bm, r, hole, t, t)
        _tube(bm, hole, hole, t, 0)
    return [_object("disc", bm, material)]


@parts.add("hinged_door")
def hinged_door(p, material):
    """Round door hinged at its top edge, swung open by `open_deg`."""
    r = p["diameter"] / 2
    bm = bmesh.new()
    _tube(bm, r, r, 0, p.get("thickness", 0.09), cap0=True, cap1=True)
    door = _object("door", bm, material)
    a = math.radians(p.get("open_deg", 105))
    door.matrix_world = (Matrix.Translation((0, 0, r)) @ Matrix.Rotation(-a, 4, "Y")
                         @ Matrix.Translation((0, 0, -r)))
    return [door]


@parts.add("solar_wing")
def solar_wing(p, material):
    """Flat wing of solar cells in a frame, on a mast along +Y or -Y."""
    side = p.get("side", 1)
    L, W, base = p["length"], p["width"], p.get("mast_base", 2.0)
    tilt = math.radians(p.get("tilt_deg", 20))
    rot = Matrix.Rotation(tilt, 4, "Y")
    center = (0, side * (base + L / 2), 0)
    gap = 0.14
    bm = bmesh.new()
    for s in (-1, 1):
        _box(bm, (s * (W / 4 + gap / 4), center[1], 0), (W / 2 - gap / 2, L, 0.03), rot)
    cells = _object("cells", bm, material, smooth=False)
    bm = bmesh.new()
    for s in (-1, 1):
        cx = s * (W / 4 + gap / 4)
        pw = W / 2 - gap / 2
        for e in (-1, 1):
            _box(bm, (cx + e * pw / 2, center[1], 0), (0.05, L + 0.05, 0.07), rot)
            _box(bm, (cx, center[1] + e * L / 2, 0), (pw, 0.05, 0.07), rot)
    _box(bm, (0, center[1], 0), (0.1, L + 0.05, 0.1), rot)
    _box(bm, (0, side * (base / 2 + 0.6), 0), (0.1, base - 1.0, 0.1), rot)
    frame = _object("frame", bm, mats.get("panel_grey"), smooth=False)
    return [cells, frame]


@parts.add("dish_on_boom")
def dish_on_boom(p, material):
    """Parabolic dish on a straight mast along +Z or -Z."""
    side = p.get("side", 1)
    r, boom = p["diameter"] / 2, p["boom"]
    depth = r * 0.42
    bm = bmesh.new()
    rows, n = 14, 64
    verts = []
    for i in range(rows + 1):
        u = (i + 0.02) / rows
        row = []
        for j in range(n):
            a = 2 * math.pi * j / n
            rr = r * u
            row.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), depth * u * u)))
        verts.append(row)
    for i in range(rows):
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((verts[i][j], verts[i][k], verts[i + 1][k], verts[i + 1][j]))
    aim = Matrix.Translation((0, 0, side * boom)) @ Matrix.Rotation(math.radians(p.get("aim_deg", 28)), 4, "Y")
    if side < 0:
        aim = aim @ Matrix.Rotation(math.pi, 4, "X")
    bmesh.ops.transform(bm, matrix=aim, verts=bm.verts)
    dish = _object("dish", bm, material)
    solid = dish.modifiers.new("solid", "SOLIDIFY")
    solid.thickness = 0.03
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.05, radius2=0.05, depth=boom,
                          matrix=Matrix.Translation((0, 0, side * boom / 2)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.045, radius2=0.012, depth=r * 0.75,
                          matrix=aim @ Matrix.Translation((0, 0, r * 0.38)))
    mast = _object("mast", bm, mats.get("panel_grey"))
    return [dish, mast]


@parts.add("box")
def box(p, material):
    bm = bmesh.new()
    L, W, H = p["length"], p["width"], p["height"]
    _box(bm, (L / 2, 0, 0), (L, W, H))
    return [_object("box", bm, material, smooth=False, bevel=min(L, W, H) * 0.03)]


@parts.add("sphere")
def sphere(p, material):
    bm = bmesh.new()
    r = p["diameter"] / 2
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=r, matrix=Matrix.Translation((r, 0, 0)))
    return [_object("sphere", bm, material)]


@parts.add("cone")
def cone(p, material):
    bm = bmesh.new()
    _tube(bm, p["diameter"] / 2, p.get("tip_diameter", 0.0) / 2 + 1e-4, 0, p["length"], cap0=True, cap1=True)
    return [_object("cone", bm, material)]


@parts.add("gear")
def gear(p, material):
    """Toothed wheel in the YZ plane, so its axle runs along X."""
    r, teeth, t = p["diameter"] / 2, int(p["teeth"]), p.get("thickness", p["diameter"] * 0.15)
    depth = min(r * 0.14, 2.2 * r / teeth)
    root, tip = r - depth, r
    outline = []
    for i in range(teeth):
        for u, radius in ((0.0, root), (0.18, root), (0.30, tip), (0.70, tip), (0.82, root)):
            a = 2 * math.pi * (i + u) / teeth
            outline.append((radius * math.cos(a), radius * math.sin(a)))
    bm = bmesh.new()
    front = [bm.verts.new((0, y, z)) for y, z in outline]
    back = [bm.verts.new((t, y, z)) for y, z in outline]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    ob = [_object("gear", bm, material, smooth=False)]
    hole = p.get("hole", 0)
    if hole:
        bm = bmesh.new()
        _tube(bm, hole / 2, hole / 2, -0.01, t + 0.01, cap0=True, cap1=True)
        ob.append(_object("axle", bm, mats.get("black_inner")))
    return ob
