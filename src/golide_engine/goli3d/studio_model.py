"""Goli's studio in real 3D (owner 2026-11-21): built once in Blender, rendered as two plates per format.

python studio_model.py '{"fmt": "short"|"long", "pass": "back"|"front"|"full", "scale": 1.0, "samples": 64}' out.png

back  = wall, video wall (TV), neon GOLIDE ring, shelves, chair: everything behind Goli (opaque)
front = desk, laptop, mug, podcast mic: everything in front of Goli (transparent around it)
full  = both (a preview)
Every part is placed by the pixel slots of edit/studio.py LAYOUTS, so screen content, words and Goli drop in unchanged.
A sidecar <out>.json gives the TV screen's corners in pixels.
"""
import json
import math
import sys

import bpy  # noqa: loads bmesh
import bmesh
from mathutils import Vector

SPEC = json.loads(sys.argv[-2]) if len(sys.argv) > 2 else {}
OUT = sys.argv[-1]
FMT = SPEC.get("fmt", "short")
PASS = SPEC.get("pass", "full")

# the pixel slots of the flat studio (edit/studio.py LAYOUTS), so nothing else has to move
LAY = {
    "long": dict(w=1920, h=1080, desk_y=772, seat_x=640, size=820, wall=(0, 0, 1.0), neon=(0, 0, 1.0), shelf=(0, 0, 1.0)),
    "short": dict(w=1080, h=1920, desk_y=1560, seat_x=540, size=900, wall=(-1361, 48, 1.28), neon=None, shelf=(-80, 540, 1.0)),
}[FMT]
W, H = LAY["w"], LAY["h"]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


# ------------------------------------------------------------------ camera and pixel -> world
# 2026-11-21 (owner): one premium camera shot. Raised and tilted down a little, so the table top shows its depth.
LENS, SENSOR = 50.0, 36.0
TILT = math.radians(6.0)
CAM = Vector((0, -6.0, 1.55))           # wall plane at y = 0 (6 units away)
from mathutils import Euler  # noqa: E402

ROT = Euler((math.pi / 2 - TILT, 0, 0)).to_matrix()


def _ray(px, py):
    big = (SENSOR / 2) / LENS
    hx, hz = (big, big * H / W) if W >= H else (big * W / H, big)
    return ROT @ Vector(((px / W - 0.5) * 2 * hx, (0.5 - py / H) * 2 * hz, -1.0))


def P(px, py, d):
    """The world point that lands on pixel (px, py) on the upright plane d units in front of the camera."""
    r = _ray(px, py)
    return CAM + r * (d / r.y)


def PZ(px, py, z):
    """The world point that lands on pixel (px, py) on the level plane at height z (the table top, the floor)."""
    r = _ray(px, py)
    return CAM + r * ((z - CAM.z) / r.z)


def U(d, py=None):
    """World units per pixel on the upright plane at distance d."""
    py = H / 2 if py is None else py
    return (P(W / 2 + 0.5, py, d) - P(W / 2 - 0.5, py, d)).length


def g(key, x, y):
    """A point of a group (wall, neon, shelf) through its layout transform, in pixels."""
    t = LAY[key]
    return (t[0] + x * t[2], t[1] + y * t[2]) if t else None


# ------------------------------------------------------------------ materials
def rgb(h):
    return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5))


def mat(name, color, rough=0.5, metal=0.0, coat=0.0, sheen=0.0, emit=0.0, ecolor=None, trans=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.1
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb(ecolor or color), 1)
        b.inputs["Emission Strength"].default_value = emit
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
    return m


def wood(name, base, dark, scale=6.0):
    """Walnut-like wood: a stretched noise grain."""
    m = mat(name, base, 0.6, coat=0.08)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale * 0.15, scale * 0.15, scale * 6)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*rgb(dark), 1); ramp.color_ramp.elements[1].color = (*rgb(base), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


M = dict(
    slat=wood("slat", "#1A2240", "#0E1428", 4), gap=mat("gap", "#05070D", 0.9),
    floor=mat("floor", "#0B0E16", 0.35, coat=0.4),
    bezel=mat("bezel", "#07080C", 0.25, coat=0.8), screen=mat("screen", "#03050C", 0.5, emit=0.3, ecolor="#0C1A44"),
    gold=mat("gold", "#E8B84A", 0.22, metal=1.0), gold_glow=mat("gold_glow", "#FFD27A", 0.3, emit=9.0, ecolor="#FFC75A"),
    blue_glow=mat("blue_glow", "#3D6CFF", 0.3, emit=6.0, ecolor="#3D6CFF"),
    shelf=wood("shelfwood", "#6B4A2E", "#3E2817", 8), metal=mat("metal", "#2C303A", 0.35, metal=0.9),
    desk=wood("deskwood", "#5A3A22", "#2E1C10", 5), desk_side=mat("desk_side", "#14161D", 0.5, coat=0.3),
    alu=mat("alu", "#B7BCC6", 0.25, metal=1.0), alu_dark=mat("alu_dark", "#8E949F", 0.3, metal=1.0),
    ceramic=mat("ceramic", "#F4F1EA", 0.18, coat=0.6), coffee=mat("coffee", "#3B2212", 0.1, coat=1.0),
    mic=mat("mic", "#1B1D23", 0.35, metal=0.6), grille=mat("grille", "#2E323B", 0.5, metal=0.8),
    leather=mat("leather", "#121318", 0.42, coat=0.35, sheen=0.2), pot=mat("pot", "#E9E2D3", 0.5),
    leaf=mat("leaf", "#2F9E5B", 0.45, sheen=0.3), cube=mat("cube", "#3D6CFF", 0.2, coat=1.0, emit=1.5, ecolor="#3D6CFF"),
    trophy_base=mat("trophy_base", "#151821", 0.3, coat=0.6),
)
BOOKS = [mat(f"book{i}", c, 0.55, coat=0.2) for i, c in enumerate(("#E8462F", "#2450E6", "#F2C14E", "#12A36B", "#7B3FE4"))]

M["screen"].node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.0
M["screen"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
back_col = bpy.data.collections.new("back"); sc.collection.children.link(back_col)
front_col = bpy.data.collections.new("front"); sc.collection.children.link(front_col)


def put(o, col):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def shade(o, bevel=0.0, seg=3):
    for p in o.data.polygons:
        p.use_smooth = True
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = seg; b.limit_method = "ANGLE"
    o.data.shade_auto_smooth() if hasattr(o.data, "shade_auto_smooth") else None
    return o


def box(center, size, m, col, bevel=0.01, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    return put(shade(o, bevel), col)


def cyl(center, r, depth, m, col, rot=(0, 0, 0), verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=center, rotation=rot)
    o = bpy.context.object
    o.data.materials.append(m)
    return put(shade(o, bevel), col)


def sph(center, scale, m, col):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=center)
    o = bpy.context.object
    o.scale = scale
    o.data.materials.append(m)
    return put(shade(o), col)


def tube(points, r, m, col):
    cu = bpy.data.curves.new("t", "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = r; cu.bevel_resolution = 6; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (*p, 1)
    o = bpy.data.objects.new("t", cu); o.data.materials.append(m)
    col.objects.link(o)
    return o


def area(name, loc, energy, size, color, target, col=None, shape="RECTANGLE", sy=None):
    d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.color = color; d.shape = shape
    d.size = size; d.size_y = sy or size
    o = bpy.data.objects.new(name, d); o.location = loc
    (col or sc.collection).objects.link(o)
    t = bpy.data.objects.new(name + "_t", None); t.location = target; sc.collection.objects.link(t)
    c = o.constraints.new("TRACK_TO"); c.target = t
    return o


# ------------------------------------------------------------------ back: wall, TV, neon, shelves, chair
DW = 6.0                                    # the wall's distance from the camera
y_wall = CAM.y + DW
top_left, bot_right = P(-60, -60, DW), P(W + 60, H + 60, DW)
span_w, span_h = bot_right.x - top_left.x, top_left.z - bot_right.z
slat_w = 58 * U(DW)
x = top_left.x
while x < bot_right.x:                       # vertical acoustic slats with dark gaps
    box((x + slat_w / 2, y_wall - 0.03, (top_left.z + bot_right.z) / 2), (slat_w, 0.06, span_h), M["slat"], back_col, 0.006)
    x += 66 * U(DW)
box((0, y_wall + 0.02, (top_left.z + bot_right.z) / 2), (span_w + 1, 0.02, span_h + 1), M["gap"], back_col, 0)
# warm LED uplight at the foot of the wall
f0, f1 = P(-40, H - 6, DW - 0.25), P(W + 40, H - 6, DW - 0.25)
box(((f0.x + f1.x) / 2, y_wall - 0.25, f0.z), (f1.x - f0.x, 0.03, 0.03), M["gold_glow"], back_col, 0)
area("uplight", ((f0.x + f1.x) / 2, y_wall - 0.5, f0.z - 0.1), 900, f1.x - f0.x, (1.0, 0.78, 0.45),
     ((f0.x + f1.x) / 2, y_wall, f0.z + 3), back_col, sy=0.2)

# the video wall: a big flat TV with a slim bezel; the screen is left plain (content is laid on in the video)
x0, y0 = g("wall", 1124, 124); x1, y1 = g("wall", 1846, 636)
DT = DW - 0.18
a, b = P(x0, y0, DT), P(x1, y1, DT)
cx, cz, sw, shh = (a.x + b.x) / 2, (a.z + b.z) / 2, b.x - a.x, a.z - b.z
bez = 18 * U(DT) * (LAY["wall"][2] if LAY["wall"] else 1)
box((cx, CAM.y + DT + 0.05, cz), (sw + 2 * bez, 0.08, shh + 2 * bez), M["bezel"], back_col, 0.012)
scr = box((cx, CAM.y + DT - 0.0, cz), (sw, 0.01, shh), M["screen"], back_col, 0)
box((cx, CAM.y + DT + 0.12, cz), (sw * 0.3, 0.06, shh * 0.3), M["metal"], back_col, 0.01)      # wall mount
halo = area("tv_halo", (cx, CAM.y + DT + 0.14, cz), 260, sw * 0.9, (0.25, 0.4, 1.0), (cx, CAM.y + DW + 1, cz), back_col, sy=shh * 0.9)
glow = mat("tvglow", "#3D6CFF", 0.5, emit=3.0, ecolor="#2C55E0")
area("tv_wash", (cx, CAM.y + DT - 0.4, cz), 220, sw, (0.35, 0.5, 1.0), (cx, CAM.y + DT - 3, cz - 1.5), back_col, sy=shh)
screen_px = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

# GOLIDE neon ring (long only; the logo mark itself is drawn on top as before)
if LAY["neon"]:
    nx, ny = g("neon", 170, 170)
    c = P(nx, ny, DW - 0.1)
    bpy.ops.mesh.primitive_torus_add(major_radius=66 * U(DW - 0.1), minor_radius=5 * U(DW - 0.1), location=c, rotation=(math.pi / 2, 0, 0))
    t = put(shade(bpy.context.object), back_col); t.data.materials.append(M["gold_glow"])
    logo = SPEC.get("neon_logo")
    if logo:                                  # the GOLIDE mark glowing inside the ring
        im = bpy.data.images.load(logo)
        lm = bpy.data.materials.new("neonlogo"); lm.use_nodes = True
        ln = lm.node_tree; bsdf = ln.nodes["Principled BSDF"]
        tex = ln.nodes.new("ShaderNodeTexImage"); tex.image = im
        ln.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"]); ln.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        ln.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"]); bsdf.inputs["Emission Strength"].default_value = 6.0
        r_ = 60 * U(DW - 0.1)
        bpy.ops.mesh.primitive_plane_add(size=2 * r_, location=c + Vector((0, -0.01, 0)), rotation=(math.pi / 2, 0, 0))
        lp_ = put(bpy.context.object, back_col); lp_.data.materials.append(lm)
    pl = bpy.data.lights.new("neon", "POINT"); pl.energy = 60; pl.color = (1, 0.8, 0.45); pl.shadow_soft_size = 0.3
    po = bpy.data.objects.new("neon", pl); po.location = c + Vector((0, -0.3, 0)); back_col.objects.link(po)

# floating shelves: books, trophy, LED cube, plant
DS = DW - 0.45
for sy_px in (470, 640):
    sx0, sy0 = g("shelf", 96, sy_px); sx1, _ = g("shelf", 396, sy_px)
    p0, p1 = P(sx0, sy0, DS), P(sx1, sy0, DS)
    box(((p0.x + p1.x) / 2, CAM.y + DS + 0.1, p0.z - 0.025), (p1.x - p0.x, 0.42, 0.05), M["shelf"], back_col, 0.008)
    box(((p0.x + p1.x) / 2, CAM.y + DS - 0.08, p0.z - 0.06), (p1.x - p0.x - 0.04, 0.01, 0.01), M["gold_glow"], back_col, 0)
u = U(DS)
bx = 120
for i, (w_, h_) in enumerate(((26, 92), (20, 104), (30, 86), (22, 98), (18, 80))):
    px_, py_ = g("shelf", bx + w_ / 2, 470)
    base = P(px_, py_, DS)
    tilt = (0, -0.12 if i == 4 else 0, 0)
    box((base.x, CAM.y + DS + 0.1, base.z + h_ * u / 2), (w_ * u * 0.95, 0.3, h_ * u), BOOKS[i], back_col, 0.006, rot=tilt)
    bx += w_ + 4
tx, ty = g("shelf", 320, 470)
tb = P(tx, ty, DS)
box((tb.x, CAM.y + DS + 0.1, tb.z + 0.03), (0.1, 0.1, 0.06), M["trophy_base"], back_col, 0.008)
cyl((tb.x, CAM.y + DS + 0.1, tb.z + 0.09), 0.016, 0.07, M["gold"], back_col)
sph((tb.x, CAM.y + DS + 0.1, tb.z + 0.18), (0.075, 0.075, 0.07), M["gold"], back_col)
for s in (-1, 1):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.008, location=(tb.x + s * 0.078, CAM.y + DS + 0.1, tb.z + 0.19), rotation=(math.pi / 2, 0, 0))
    put(shade(bpy.context.object), back_col).data.materials.append(M["gold"])
cx_, cy_ = g("shelf", 150, 640)
cb = P(cx_, cy_, DS)
box((cb.x, CAM.y + DS + 0.1, cb.z + 30 * u), (60 * u, 60 * u, 60 * u), M["cube"], back_col, 0.02)
px_, py_ = g("shelf", 304, 640)
pb = P(px_, py_, DS)
cyl((pb.x, CAM.y + DS + 0.1, pb.z + 25 * u), 34 * u, 50 * u, M["pot"], back_col, bevel=0.01)
for k, (ang, ln) in enumerate(((-35, 1.0), (-12, 1.2), (8, 1.25), (30, 1.05), (52, 0.9), (-55, 0.85))):
    a_ = math.radians(ang)
    tip = Vector((pb.x + math.sin(a_) * 70 * u * ln, CAM.y + DS + 0.1 + (k % 2) * 0.06, pb.z + 50 * u + math.cos(a_) * 90 * u * ln))
    mid = Vector((pb.x, CAM.y + DS + 0.1, pb.z + 50 * u)).lerp(tip, 0.55)
    sph(tuple(mid), (18 * u, 6 * u, 48 * u * ln), M["leaf"], back_col).rotation_euler = (0, a_, 0)

# the chair behind Goli: a high-backed leather chair with gold piping
k = LAY["size"] / 820
DC = 4.7
cbase = P(LAY["seat_x"], LAY["desk_y"], DC)
cu_ = U(DC)
ch_w, ch_h = 470 * k * cu_, 450 * k * cu_
bm = bmesh.new()
pts = []
for i in range(41):                          # back outline: straight sides, rounded top
    t = i / 40
    if t < 0.5:
        a_ = math.pi * (t / 0.5)
        pts.append((-math.cos(a_) * ch_w / 2 * (0.92 + 0.08 * math.sin(a_)), ch_h - (1 - math.sin(a_)) * 0.18 * ch_h))
    else:
        tt = (t - 0.5) / 0.5
        pts.append((ch_w / 2 * (1 - 0.06 * tt) if tt < 0.5 else ch_w / 2 * 1.04, ch_h * (1 - tt) * 0.0 + (0.82 * ch_h) * (1 - tt)))
outline = [(-ch_w * 0.47, 0)] + [(-ch_w / 2, ch_h * 0.82)] + [(math.cos(math.pi * (1 - j / 20)) * ch_w / 2, ch_h * 0.82 + math.sin(math.pi * j / 20) * ch_h * 0.18) for j in range(21)] + [(ch_w / 2, ch_h * 0.82), (ch_w * 0.47, 0)]
vs = [bm.verts.new((x_, 0, z_)) for x_, z_ in outline]
f = bm.faces.new(vs)
ext = bmesh.ops.extrude_face_region(bm, geom=[f])
for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]:
    v.co.y += 0.32
me = bpy.data.meshes.new("chair"); bm.to_mesh(me); bm.free()
chair = bpy.data.objects.new("chair", me); back_col.objects.link(chair); me.materials.append(M["leather"])
chair.location = (cbase.x, CAM.y + DC, cbase.z)
shade(chair, 0.05, 5)
sub = chair.modifiers.new("sub", "SUBSURF"); sub.levels = sub.render_levels = 2
pip = [(cbase.x + x_ * 0.9, CAM.y + DC - 0.02, cbase.z + z_ * 0.95 + 0.04) for x_, z_ in outline[1:-1]]
tube(pip, 0.012, M["gold"], back_col)
for s in (-1, 1):                            # stitched panels
    tube([(cbase.x + s * ch_w * 0.18, CAM.y + DC - 0.02, cbase.z + 0.1), (cbase.x + s * ch_w * 0.18, CAM.y + DC - 0.02, cbase.z + ch_h * 0.88)], 0.006, M["gold"], back_col)

# ------------------------------------------------------------------ front: the table, laptop, mug, mic
# 2026-11-21 (owner): it must read as a table: a thick rounded top with depth, overhanging a recessed front panel,
# legs at both ends, the floor beside and under them, its shadow on the floor.
DD = 3.75                                    # the table's front edge
k = LAY["size"] / 820
back_px = LAY["desk_y"] - 18 * k             # the top's back edge sits just over Goli's waist
d_back = DD + 0.95
top_z = P(LAY["seat_x"], back_px, d_back).z
front = PZ(LAY["seat_x"], 0, top_z)          # just for x scale
du = U(DD)
half = (W * 0.53 if FMT == "short" else 760) * du
cxT = P(LAY["seat_x"] if FMT == "long" else W / 2, 0, DD).x
T = 0.085                                    # top thickness
top_d = d_back - DD
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
me = bpy.data.meshes.new("tabletop"); bm.to_mesh(me); bm.free()
tt = bpy.data.objects.new("tabletop", me); front_col.objects.link(tt); me.materials.append(M["desk"])
tt.location = (cxT, CAM.y + DD + top_d / 2, top_z - T / 2); tt.scale = (2 * half, top_d, T)
bpy.context.view_layer.objects.active = tt
shade(tt, 0.03, 6)
# gold inlay strip along the top's front edge and a soft LED under the overhang
box((cxT, CAM.y + DD - 0.005, top_z - T * 0.55), (2 * half - 0.06, 0.008, 0.012), M["gold_glow"], front_col, 0)
floor_z = top_z - 0.95
# recessed front (modesty) panel: dark wood with a gold-framed inset, set back from the top's edge
panel_y = CAM.y + DD + 0.16
ph = top_z - T - floor_z - 0.12
box((cxT, panel_y, floor_z + 0.12 + ph / 2), (2 * half - 0.5, 0.05, ph), M["desk_side"], front_col, 0.01)
box((cxT, panel_y - 0.03, floor_z + 0.12 + ph / 2), (2 * half - 0.9, 0.02, ph - 0.22), M["desk"], front_col, 0.01)
for zz in (floor_z + 0.12 + 0.11, top_z - T - 0.11):
    box((cxT, panel_y - 0.045, zz), (2 * half - 0.9, 0.01, 0.01), M["gold"], front_col, 0)
for sx_ in (-1, 1):
    box((cxT + sx_ * (half - 0.45), panel_y - 0.045, floor_z + 0.12 + ph / 2), (0.01, 0.01, ph - 0.22), M["gold"], front_col, 0)
# legs: tapered blocks at both ends with gold feet
for sx_ in (-1, 1):
    lx = cxT + sx_ * (half - 0.16)
    for ly in (CAM.y + DD + 0.12, CAM.y + d_back - 0.12):
        box((lx, ly, (floor_z + top_z - T) / 2), (0.1, 0.1, top_z - T - floor_z), M["desk_side"], front_col, 0.015)
        cyl((lx, ly, floor_z + 0.015), 0.07, 0.03, M["gold"], front_col, bevel=0.005)
area("under", (cxT, CAM.y + DD + 0.2, top_z - T - 0.03), 25, 2 * half - 0.3, (1.0, 0.8, 0.5), (cxT, CAM.y + DD + 0.2, floor_z), front_col, sy=0.05)
# the studio floor: dark, glossy, catching the lights
fm = mat("studiofloor", "#0D1018", 0.18, coat=0.6)
box((0, CAM.y + 4, floor_z - 0.025), (40, 16, 0.05), fm, back_col, 0)
dtop = Vector((0, 0, top_z))


def desk_point(px, depth_px=0.0):
    """A point on the table top at pixel x (relative to the seat, like the flat set), pushed back by depth_px."""
    xx = LAY["seat_x"] + (px - 640) * k
    p = P(xx, back_px, d_back - 0.35 - depth_px * du)
    return Vector((p.x, p.y, top_z))


# laptop (right): open, lid facing the camera with the glowing mark
lp = desk_point(1070 if FMT == "long" else 930, 2)
lw, lh = 290 * k * du, 186 * k * du
box((lp.x, lp.y + 0.12, lp.z + 0.012), (lw * 1.05, lw * 0.7, 0.024), M["alu"], front_col, 0.01)
lid = box((lp.x, lp.y + 0.36, lp.z + lh / 2 + 0.02), (lw, 0.025, lh), M["alu"], front_col, 0.012, rot=(math.radians(-14), 0, 0))
if SPEC.get("neon_logo"):                    # the GOLIDE mark glowing on the lid
    im2 = bpy.data.images.load(SPEC["neon_logo"])
    lm2 = bpy.data.materials.new("lidlogo"); lm2.use_nodes = True
    n2 = lm2.node_tree; b2 = n2.nodes["Principled BSDF"]
    t2 = n2.nodes.new("ShaderNodeTexImage"); t2.image = im2
    n2.links.new(t2.outputs["Color"], b2.inputs["Base Color"]); n2.links.new(t2.outputs["Color"], b2.inputs["Emission Color"])
    n2.links.new(t2.outputs["Alpha"], b2.inputs["Alpha"]); b2.inputs["Emission Strength"].default_value = 4.0
    r2 = 46 * k * du
    bpy.ops.mesh.primitive_plane_add(size=2 * r2, location=(lp.x, lp.y + 0.33, lp.z + lh * 0.52), rotation=(math.pi / 2 - math.radians(14), 0, 0))
    put(bpy.context.object, front_col).data.materials.append(lm2)
else:
    cyl((lp.x, lp.y + 0.33, lp.z + lh * 0.52), 38 * k * du, 0.01, M["gold_glow"], front_col, rot=(math.pi / 2, 0, 0))
# mug (left), with coffee
mp = desk_point(880, 0) if FMT == "long" else desk_point(360, -110)
mr, mh = 39 * k * du, 96 * k * du
cyl((mp.x, mp.y, mp.z + mh / 2), mr, mh, M["ceramic"], front_col, bevel=0.006)
cyl((mp.x, mp.y, mp.z + mh - 0.012), mr * 0.86, 0.01, M["coffee"], front_col)
bpy.ops.mesh.primitive_torus_add(major_radius=mh * 0.24, minor_radius=mh * 0.06, location=(mp.x + mr * 1.05, mp.y, mp.z + mh * 0.55), rotation=(math.pi / 2, 0, 0))
put(shade(bpy.context.object), front_col).data.materials.append(M["ceramic"])
# podcast mic on a boom arm (beside Goli's face, between the mug and him)
mb = desk_point(300 if FMT == "short" else 175)
arm = [Vector((mb.x, mb.y, mb.z + 0.01)), Vector((mb.x - 0.04, mb.y + 0.02, mb.z + 150 * k * du)),
       Vector((mb.x + 40 * k * du, mb.y - 0.02, mb.z + 260 * k * du))]
cyl((mb.x, mb.y, mb.z + 0.015), 26 * k * du, 0.03, M["mic"], front_col, bevel=0.005)
tube([tuple(p) for p in arm], 7 * k * du, M["metal"], front_col)
sph(tuple(arm[1]), (12 * k * du,) * 3, M["mic"], front_col)
head = arm[2] + Vector((10 * k * du, 0, 60 * k * du))
body = cyl(tuple(head), 31 * k * du, 150 * k * du, M["grille"], front_col, rot=(0, math.radians(12), 0), bevel=0.01)
cyl(tuple(head), 34 * k * du, 14 * k * du, M["gold"], front_col, rot=(0, math.radians(12), 0))
sph(tuple(head + Vector((math.sin(math.radians(12)) * 75 * k * du, 0, math.cos(math.radians(12)) * 75 * k * du))), (31 * k * du,) * 3, M["grille"], front_col)

# ------------------------------------------------------------------ lights, world, camera, passes
area("key", (CAM.x - 3.0, CAM.y + 2.2, CAM.z + 2.4), 420, 2.0, (1.0, 0.92, 0.82), (0, CAM.y + DD, dtop.z))
area("fill", (CAM.x + 3.5, CAM.y + 1.5, CAM.z + 1.0), 120, 3.0, (0.75, 0.82, 1.0), (0, CAM.y + DD, dtop.z))
area("rim", (CAM.x + 2.5, CAM.y + DW - 0.6, CAM.z + 3.5), 500, 2.0, (0.5, 0.6, 1.0), (0, CAM.y + DC, dtop.z + 1))
world = bpy.data.worlds.new("w"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.025, 0.05, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.15
sc.world = world

cam = bpy.data.cameras.new("cam"); cam.lens = LENS; cam.sensor_width = SENSOR; cam.sensor_fit = "AUTO"
co = bpy.data.objects.new("cam", cam); co.location = CAM; co.rotation_euler = (math.pi / 2, 0, 0)
sc.collection.objects.link(co); sc.camera = co
co.rotation_euler = (math.pi / 2 - TILT, 0, 0)
cam.dof.use_dof = True                        # a premium lens: the set behind Goli a touch soft
cam.dof.focus_distance = (CAM.y + DD + 0.9) - CAM.y
cam.dof.aperture_fstop = SPEC.get("fstop", 3.2)

scale = SPEC.get("scale", 1.0)
sc.render.resolution_x, sc.render.resolution_y = int(W * scale), int(H * scale)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.cycles.samples = SPEC.get("samples", 64); sc.cycles.use_denoising = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.image_settings.color_mode = "RGBA"
vl = sc.view_layers[0]
if PASS == "front":                           # the back stays in the scene (light, reflections) but is cut out
    sc.render.film_transparent = True
    vl.layer_collection.children["back"].holdout = True
elif PASS == "back":
    vl.layer_collection.children["front"].exclude = True
# (no compositor bloom: the glowing parts carry their own light)
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
bpy.context.view_layer.update()
mug_top = world_to_camera_view(sc, co, Vector((mp.x, mp.y, mp.z + mh)))
neon_px = None
with open(OUT + ".json", "w") as fh:
    json.dump({"screen": screen_px, "fmt": FMT, "w": W, "h": H,
               "mug_top": [mug_top.x * W, (1 - mug_top.y) * H]}, fh)
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
