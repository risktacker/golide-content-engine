"""Goli 3D (v4): the approved v1 look + expressions, haircuts, outfits, glasses styles, poses.

python goli4.py '<json spec>' out.png
spec: expr, pose, hair, outfit, glasses ('none' = off), framing ('full'|'bust'), bg ('stage'|'transparent'),
      mouth_open (talking: overrides the expression's openness), size, samples, yaw
"""
import json
import math
import sys

import bpy  # noqa: loads bmesh
import bmesh
from mathutils import Matrix, Vector

SPEC = json.loads(sys.argv[-2]) if len(sys.argv) > 2 else {}
OUT = sys.argv[-1]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


# ------------------------------------------------------------------ materials
def rgb(h):
    return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5))


def mat(name, color, rough=0.5, metal=0.0, coat=0.0, sheen=0.0, sss=0.0, alpha=1.0, trans=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.15
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.4, 0.2, 0.1)
        b.inputs["Subsurface Scale"].default_value = 0.08
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
        b.inputs["IOR"].default_value = 1.33
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb(color), 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


SKIN = mat("skin", "#FFE3BE", 0.55, sss=0.25)
SCALE = mat("scale", "#F59A1C", 0.3, coat=0.7)
SCALE_D = mat("scale_dark", "#8A4A0C", 0.45, coat=0.3)
FADE = mat("fade", "#5C2F08", 0.6, coat=0.1)
EAR_IN = mat("ear_in", "#FFB9A0", 0.6, sss=0.2)
WHITE = mat("white", "#F7F5F0", 0.35)
GOLD = mat("gold", "#E8B84A", 0.25, metal=1.0)
SILVER = mat("silver", "#D8DCE2", 0.2, metal=1.0)
ACETATE = mat("acetate", "#141416", 0.25, coat=0.9)
NOSE = mat("nose", "#2A1810", 0.18, coat=0.5)
BROW = mat("brow", "#4A230A", 0.6)
LASH = mat("lash", "#2E1607", 0.6)
MOUTH = mat("mouth", "#5E1A1E", 0.5)
TONGUE = mat("tongue", "#F07A8A", 0.45, sss=0.3)
LIP = mat("lip", "#E9B98F", 0.5, sss=0.2)
TEETH = mat("teeth", "#FBF8F2", 0.3, coat=0.4)
LEG = mat("leg", "#D47A1E", 0.5)
SHOE = mat("shoe", "#FAFAFA", 0.4)
FLOOR = mat("floor", "#E9E4F2", 0.9)
BLUSH = mat("blush", "#FF8A8A", 0.7, alpha=0.6)
WATER = mat("water", "#8FD3FF", 0.05, coat=1.0, trans=0.5, emit=0.3)
ANGER = mat("anger", "#E8242B", 0.4, emit=0.4)


def glass_mat():
    m = bpy.data.materials.new("glass")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.97, 0.98, 1.0, 1)
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.2
    b.inputs["Coat Weight"].default_value = 0.3
    return m


GLASS = glass_mat()


def eye_mat(name, gaze, ps, sparkle):
    """v1's eye look (brown iris, black pupil, white catchlight) painted on the eyeball, so lids cover it cleanly."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Coat Weight"].default_value = 0.5
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Object"], nrm.inputs[0])

    def dot(v):
        d = nt.nodes.new("ShaderNodeVectorMath"); d.operation = "DOT_PRODUCT"
        d.inputs[1].default_value = tuple(Vector(v).normalized())
        nt.links.new(nrm.outputs[0], d.inputs[0])
        return d.outputs["Value"]

    g = Vector((gaze[0] * 0.55, -1, gaze[1] * 0.5)).normalized()
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    cr.elements[0].position = 0.0; cr.elements[0].color = (1, 1, 1, 1)
    cr.elements[1].position = 1.0; cr.elements[1].color = (*rgb("#0A0604"), 1)
    ci, cp = math.cos(0.58), math.cos(0.33 * ps)
    for pos, col in ((ci, "#3E220A"), (ci + (1 - ci) * 0.1, "#5A3412"), (cp, "#0A0604")):
        e = cr.elements.new(pos); e.color = (*rgb(col), 1)
    nt.links.new(dot(g), ramp.inputs["Fac"])
    hls = [((g.x - 0.4, g.y, g.z + 0.38), 0.988)]
    if sparkle:
        hls += [((g.x + 0.3, g.y, g.z - 0.3), 0.992), ((g.x + 0.35, g.y, g.z + 0.25), 0.994), ((g.x - 0.2, g.y, g.z - 0.4), 0.995)]
    else:
        hls += [((g.x + 0.25, g.y, g.z - 0.28), 0.997)]
    mask = None
    for v, th in hls:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = th - 0.002
        mr.inputs["From Max"].default_value = th
        nt.links.new(dot(v), mr.inputs["Value"])
        if mask is None:
            mask = mr.outputs["Result"]
        else:
            mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
            nt.links.new(mask, mx.inputs[0]); nt.links.new(mr.outputs["Result"], mx.inputs[1])
            mask = mx.outputs[0]
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(mask, mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    mix.inputs[7].default_value = (1, 1, 1, 1)
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    em = nt.nodes.new("ShaderNodeMath"); em.operation = "MULTIPLY"; em.inputs[1].default_value = 2.5
    nt.links.new(mask, em.inputs[0]); nt.links.new(em.outputs[0], b.inputs["Emission Strength"])
    return m


# ------------------------------------------------------------------ primitives
def shade(o):
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def subsurf(o, levels=1):
    m = o.modifiers.new("sub", "SUBSURF"); m.levels = m.render_levels = levels
    return o


def sphere(loc, scale, m, rot=(0, 0, 0), seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = scale
    o.data.materials.append(m)
    return shade(o)


def capsule(a, b, r, m):
    """v1's capsule (kept for legs and drawstrings so they look exactly as approved)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.data.materials.append(m)
    shade(o); subsurf(o, 2)
    for end in (a, b):
        sphere(tuple(end), (r, r, r), m)
    return o


def curve(points, r, m, radii=None, closed=False, bezier=True):
    cu = bpy.data.curves.new("c", "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = r; cu.bevel_resolution = 6; cu.resolution_u = 14; cu.use_fill_caps = True
    if bezier:
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(points) - 1)
        for i, p in enumerate(points):
            bp = sp.bezier_points[i]; bp.co = Vector(p)
            bp.handle_left_type = bp.handle_right_type = "AUTO"
            if radii:
                bp.radius = radii[i]
    else:
        sp = cu.splines.new("POLY"); sp.points.add(len(points) - 1)
        for i, p in enumerate(points):
            sp.points[i].co = (*p, 1)
            if radii:
                sp.points[i].radius = radii[i]
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new("c", cu); sc.collection.objects.link(o); o.data.materials.append(m)
    return o


def limb(a, b, r0, r1, m):
    """A smooth tapered limb (the v2 arm)."""
    a, b = Vector(a), Vector(b)
    curve([a, a.lerp(b, 0.5), b], 1.0, m, radii=[r0, (r0 + r1) / 2, r1])
    sphere(tuple(a), (r0, r0, r0), m, seg=32)
    sphere(tuple(b), (r1, r1, r1), m, seg=32)


def plate(loc, normal, size, m, flat=0.3, long=1.1):
    """v1's scale: a rounded leaf lying on the surface."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc)
    o = bpy.context.object
    o.scale = (size, size * flat, size * long)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, -1, 0)).rotation_difference(Vector(normal).normalized())
    o.data.materials.append(m)
    return shade(o)


# ------------------------------------------------------------------ head geometry (v1)
H = Vector((0, 0, 1.78))
HR = Vector((0.6, 0.52, 0.52))
SURFS = [((0, -0.16, 1.68), (0.5, 0.42, 0.47)), ((0, -0.5, 1.56), (0.24, 0.2, 0.17))]


def front_y(x, z):
    best = -0.5
    for c, r in SURFS:
        k = 1 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
        if k > 0:
            best = min(best, c[1] - r[1] * math.sqrt(k))
    return best


def head_dir(el, az):
    return Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))


def on_head(d, k=1.1):
    return H + Vector((d.x * HR.x, d.y * HR.y, d.z * HR.z)) * k


def face_clear(d):
    return d.y < -0.25 and d.z < 0.62


# ------------------------------------------------------------------ haircuts (all built from his scales)
def hair_classic():
    rows = ((90, 1), (70, 5), (50, 8), (30, 10), (10, 12))
    for k, (el, n) in enumerate(rows):
        for i in range(n):
            az = 2 * math.pi * i / n + (k % 2) * math.pi / max(n, 1)
            d = head_dir(math.radians(el), az)
            if face_clear(d):
                continue
            plate(on_head(d), d, 0.21 - k * 0.008, SCALE)


def fade_sides(top_el=35):
    return                                   # the dark under-layer itself reads as the fade
    """A fade: the sides and back show the dark under-layer with tiny tight scales near the top line."""
    for k, el in enumerate((top_el - 4, top_el - 16)):
        n = 22
        for i in range(n):
            az = 2 * math.pi * (i + 0.5 * k) / n
            d = head_dir(math.radians(el), az)
            if face_clear(d) or d.y < -0.35:
                continue
            plate(on_head(d, 1.02), d, 0.07 - 0.015 * k, FADE)


def hair_high_top():
    """High-top fade: a tall, round-shouldered block of overlapping scales; sides faded."""
    fade_sides(36)
    C = Vector((0, -0.02, 2.0))
    for layer in range(7):
        z = 2.08 + layer * 0.075
        shrink = 1.0 if layer < 5 else (0.93 if layer == 5 else 0.82)
        rx, ry = 0.47 * shrink, 0.43 * shrink
        n = 22
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (layer % 2)) / n
            d = Vector((math.sin(a), -math.cos(a), 0.35)).normalized()
            plate(Vector((rx * math.sin(a), ry * -math.cos(a) + C.y, z)), d, 0.1, SCALE, flat=0.32, long=1.0)
    for ring, (r, n) in enumerate(((0.0, 1), (0.13, 7), (0.25, 12), (0.34, 16))):
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (ring % 2)) / max(n, 1)
            d = Vector((math.sin(a) * r, -math.cos(a) * r, 1)).normalized()
            plate((r * math.sin(a), -r * math.cos(a) + C.y, 2.6 - r * 0.15), d, 0.11, SCALE, flat=0.32, long=1.0)
    sphere((0, C.y, 2.33), (0.44, 0.4, 0.3), SCALE_D)


def hair_waves():
    """360 waves: short, flat, tight scales spiralling from the crown, low taper."""
    fade_sides(20)
    for k, el in enumerate((88, 76, 64, 52, 40, 30)):
        n = 1 if el > 85 else int(8 + k * 4)
        for i in range(n):
            az = 2 * math.pi * i / n + k * 0.35
            d = head_dir(math.radians(el), az)
            if face_clear(d):
                continue
            plate(on_head(d, 1.03), d, 0.11, SCALE, flat=0.18, long=0.7)
    # the wave ridges: thin glossy arcs
    for k, el in enumerate((80, 68, 56, 44)):
        pts = [on_head(head_dir(math.radians(el), a), 1.07) for a in [math.radians(x) for x in range(-150, 151, 15)]]
        pts = [p for p in pts if not (p.y < H.y - 0.3 and p.z < H.z + 0.3)]
        if len(pts) > 2:
            curve(pts, 0.012, SCALE_D)


def hair_cornrows():
    """Cornrows: lines of small braided scales running from the hairline to the nape, scalp showing between."""
    fade_sides(0)
    for r in range(7):
        phi = math.radians(-54 + 18 * r)
        for j in range(15):
            t = math.radians(62 + j * 9.5)
            d = Vector((math.sin(phi) * math.sin(t), -math.cos(t), math.cos(phi) * math.sin(t))).normalized()
            if d.z < -0.3:
                continue
            plate(on_head(d, 1.03), d, 0.065, SCALE, flat=0.4, long=1.3)


def hair_locs(n=16, hang=7):
    hair_classic_top(rows=((90, 1), (70, 5), (50, 8)))
    for i in range(n):
        az = math.radians(-120 + 240 * i / (n - 1)) + math.pi
        last = None
        for j in range(hang + 3):
            e = math.radians(42) - math.radians(15) * j
            if e > math.radians(-12):
                d = head_dir(e, az)
                p = on_head(d, 1.13)
            else:
                d = Vector((math.sin(az), -math.cos(az), 0))
                p = last + Vector((d.x * 0.01, d.y * 0.01, -0.095))
            sz = 0.1 - 0.004 * j
            plate(p, d, sz, SCALE if j < 2 else SCALE, flat=0.45, long=0.95)
            last = p
        sphere(tuple(last + Vector((0, 0, -0.06))), (0.05, 0.05, 0.035), GOLD)


def hair_classic_top(rows):
    for k, (el, n) in enumerate(rows):
        for i in range(n):
            az = 2 * math.pi * i / n + (k % 2) * math.pi / max(n, 1)
            d = head_dir(math.radians(el), az)
            if face_clear(d):
                continue
            plate(on_head(d), d, 0.21 - k * 0.008, SCALE)


def hair_twists():
    """Sponge twists: short upright twists of stacked scales over the top, faded sides."""
    fade_sides(28)
    for k, el in enumerate((88, 72, 58, 44, 32)):
        n = 1 if el > 85 else int(7 + 3 * k)
        for i in range(n):
            az = 2 * math.pi * i / n + 0.3 * k
            d = head_dir(math.radians(el), az)
            if face_clear(d) and el < 60:
                continue
            base = on_head(d, 1.0)
            out = (d + Vector((0, 0, 0.6))).normalized()
            for j in range(3):
                plate(base + out * (0.06 + j * 0.065), out, 0.075 - j * 0.01, SCALE, flat=0.55, long=0.9)


def hair_afro():
    """A full rounded afro: a big ball of dense small scales framing the face."""
    C, R = Vector((0, 0.18, 2.0)), Vector((0.78, 0.62, 0.64))
    for k in range(10):
        el = math.radians(90 - k * 13)
        n = max(1, int(round(34 * math.cos(el))))
        for i in range(n):
            az = 2 * math.pi * (i + 0.5 * (k % 2)) / n
            d = head_dir(el, az)
            if d.y < -0.15 and d.z < 0.5:
                continue
            p = C + Vector((d.x * R.x, d.y * R.y, d.z * R.z))
            if p.z < 1.66:
                continue
            plate(p, d, 0.12, SCALE, flat=0.5, long=0.9)
    sphere(tuple(C), tuple(R * 0.93), SCALE)


def hair_frohawk():
    """Frohawk: a tall strip of scales from the hairline to the nape, sides faded right down."""
    fade_sides(48)
    for j in range(13):
        t = math.radians(64 + j * 11)
        d = Vector((0, -math.cos(t), math.sin(t)))
        base = on_head(d, 1.0)
        for lay_, (h, sz) in enumerate(((0.1, 0.13), (0.22, 0.12), (0.32, 0.1))):
            for side in (-1, 0, 1):
                out = (d + Vector((side * 0.5, 0, 0))).normalized()
                plate(base + d * h + Vector((side * 0.075, 0, 0)), out, sz, SCALE, flat=0.45, long=1.1)


HAIR = {"classic": hair_classic, "high_top": hair_high_top, "waves": hair_waves, "cornrows": hair_cornrows,
        "locs": hair_locs, "twists": hair_twists, "afro": hair_afro, "frohawk": hair_frohawk}


# ------------------------------------------------------------------ expressions
EXPR = {
    "neutral":      dict(brow=(0, 0, 0.01), up=1.0, tilt=0, low=-1, ps=1.0, gaze=(0, 0), mouth=("smile", 1.0)),
    "happy":        dict(brow=(0.03, 0.01, 0.025), up=1.0, tilt=0, low=-0.45, ps=1.05, gaze=(0, 0.05), mouth=("smile", 1.25), extras=["blush"]),
    "laughing":     dict(brow=(0.05, 0.02, 0.03), up=0.1, tilt=0, low=0.05, ps=1.0, gaze=(0, 0), mouth=("smile", 1.8), extras=["blush"]),
    "excited":      dict(brow=(0.06, 0.02, 0.035), up=1.0, tilt=0, low=-0.6, ps=1.3, gaze=(0, 0.1), sparkle=True, mouth=("grin", 1.5), extras=["blush"]),
    "angry":        dict(brow=(-0.03, -0.07, 0), up=0.35, tilt=0.6, low=-0.6, ps=0.8, gaze=(0, 0), mouth=("gritted", 1.0), extras=["anger"]),
    "determined":   dict(brow=(-0.03, -0.06, 0), up=0.45, tilt=0.5, low=-0.5, ps=0.85, gaze=(0, 0), mouth=("gritted", 0.8)),
    "surprised":    dict(brow=(0.07, 0.02, 0.04), up=1.0, tilt=0, low=-1, ps=0.72, gaze=(0, 0), mouth=("O", 1.0)),
    "astonished":   dict(brow=(0.1, 0.03, 0.045), up=1.0, tilt=0, low=-1, ps=0.5, gaze=(0, 0), mouth=("O", 1.5), extras=["sweat"]),
    "scared":       dict(brow=(0.05, 0.08, 0), up=1.0, tilt=0, low=-1, ps=0.5, gaze=(0, 0), mouth=("wobbly", 1.0), extras=["sweat"]),
    "disappointed": dict(brow=(-0.01, 0.045, -0.01), up=0.32, tilt=-0.35, low=-0.75, ps=0.95, gaze=(0, -0.55), mouth=("frown", 0.0)),
    "crying":       dict(brow=(0.02, 0.09, -0.01), up=0.42, tilt=-0.3, low=-0.3, ps=1.0, gaze=(0, 0.1), mouth=("frown", 1.0), extras=["tears"]),
    "shy":          dict(brow=(0.02, 0.04, 0.02), up=0.6, tilt=-0.15, low=-0.55, ps=1.1, gaze=(0.6, -0.45), mouth=("wavy", 0.0), extras=["blush"]),
    "trying_hard":  dict(brow=(-0.03, -0.06, 0), up=0.3, tilt=0.5, low=-0.3, ps=0.9, gaze=(0, 0), mouth=("press", 0.0), extras=["sweat"]),
    "thinking":     dict(brow=(0, 0, 0.01), brow_r=(0.07, 0, 0.03), up=0.75, tilt=0, low=-0.8, ps=0.95, gaze=(0.55, 0.6), mouth=("smirk", 0.0)),
    "confused":     dict(brow=(-0.02, -0.03, 0), brow_r=(0.07, 0.03, 0.03), up=0.8, tilt=0, low=-0.9, ps=0.8, gaze=(-0.3, 0.45), mouth=("wavy", 0.0)),
    "smug":         dict(brow=(0, 0, 0.01), brow_r=(0.06, -0.01, 0.02), up=0.32, tilt=-0.12, low=-0.65, ps=1.0, gaze=(-0.45, 0), mouth=("smirk", 0.0)),
    "sleepy":       dict(brow=(-0.02, 0.02, 0), up=0.05, tilt=-0.25, low=-0.7, ps=1.0, gaze=(0, -0.3), mouth=("O", 0.4)),
    "hungry":       dict(brow=(0.05, 0.03, 0.03), up=1.0, tilt=0, low=-0.6, ps=1.25, gaze=(0.35, 0.5), sparkle=True, mouth=("tongue", 1.3)),
    "in_love":      dict(brow=(0.04, 0.03, 0.03), up=0.9, tilt=0, low=-0.5, ps=1.35, gaze=(0, 0.05), sparkle=True, mouth=("smile", 1.1), extras=["blush", "hearts"]),
    "savage":       dict(brow=(-0.01, -0.04, 0), brow_r=(0.03, -0.02, 0.02), up=0.4, tilt=0.3, low=-0.55, ps=0.9, gaze=(-0.2, 0), mouth=("gritted", 0.7), props=["pen"]),
}


def lay(poly, off, m, name):
    """A flat 2D shape (x, z) laid onto the snout/face surface."""
    if len(poly) < 3:
        return
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in poly]
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    for v in bm.verts:
        v.co.y = front_y(v.co.x, v.co.z) - off
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(m)
    shade(o)


def clip(poly, above, zc):
    out = []
    ins = (lambda p: p[1] >= zc) if above else (lambda p: p[1] <= zc)
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if ins(a):
            out.append(a)
        if ins(a) != ins(b):
            t = (zc - a[1]) / (b[1] - a[1]); out.append((a[0] + t * (b[0] - a[0]), zc))
    return out


MW, MZ = 0.085, 1.455      # mouth half-width and top line: the same for every shape, so the mouth stays one design


def line(fn, w=MW, r=0.011):
    pts = []
    for i in range(13):
        u = i / 6 - 1
        x, z = u * w, MZ + fn(u)
        pts.append((x, front_y(x, z) - 0.01, z))
    curve(pts, r, MOUTH, radii=[0.8] + [1.0] * 11 + [0.8])


def creases(up=True):
    for s in (-1, 1):
        cx = s * (MW + 0.012)
        dz = 0.018 if up else -0.018
        pts = [(cx, front_y(cx, MZ + 0.012) - 0.009, MZ + 0.012),
               (cx + s * 0.016, front_y(cx + s * 0.016, MZ + 0.012 + dz) - 0.008, MZ + 0.012 + dz)]
        curve(pts, 0.006, LIP, bezier=False)


def open_mouth(poly, teeth_top=False, teeth_both=False, tongue=True):
    lay(poly, 0.006, MOUTH, "mouth")
    zs = [p[1] for p in poly]
    top, bot = max(zs), min(zs)
    if teeth_top:
        lay(clip(poly, True, top - min(0.03, (top - bot) * 0.33)), 0.009, TEETH, "teeth")
    if teeth_both:
        mid = (top + bot) / 2
        lay(clip(poly, True, mid + 0.003), 0.009, TEETH, "teeth_u")
        lay(clip(poly, False, mid - 0.003), 0.009, TEETH, "teeth_l")
    if tongue:
        tong = [(MW * 0.6 * math.cos(math.pi * i / 32), bot + 0.006 + (top - bot) * 0.45 * math.sin(math.pi * i / 32) ** 0.7) for i in range(33)]
        lay(clip(poly, False, top) and [p for p in tong], 0.0085, TONGUE, "tongue")
    rim = [(x, front_y(x, z) - 0.008, z) for x, z in poly[::2]]
    curve(rim, 0.006, LIP, closed=True, bezier=False)


def build_mouth(kind, amt, talk=None):
    if talk is not None:                  # talking: the default smile, opened by the voice
        kind, amt = "smile", talk
    w = MW
    if kind in ("smile", "grin", "tongue"):
        o = 0.075 * amt
        if o < 0.004:
            line(lambda u: 0.02 * u * u)
        else:
            poly = [(-w + 2 * w * i / 48, MZ + 0.018 * (-1 + 2 * i / 48) ** 2 - 0.004) for i in range(49)]
            poly += [(w * math.cos(math.pi * i / 48), MZ - 0.004 - o * math.sin(math.pi * i / 48) ** 0.8) for i in range(1, 48)]
            open_mouth(poly, teeth_top=(kind == "grin" or amt > 1.3), tongue=True)
            if kind == "tongue":
                bot = MZ - 0.004 - o
                tp = Vector((0.02, front_y(0.02, bot) - 0.035, bot - 0.02))
                sphere(tuple(tp), (0.055, 0.04, 0.04), TONGUE, rot=(math.radians(-25), 0, 0))
                dr = tp + Vector((0.03, -0.005, -0.09))
                drop(dr, 0.022)
        creases(True)
    elif kind == "O":
        rx, rz = 0.045 + 0.012 * amt, 0.04 + 0.035 * amt
        poly = [(rx * math.cos(2 * math.pi * i / 40), MZ - rz + rz * math.sin(2 * math.pi * i / 40)) for i in range(40)]
        open_mouth(poly, tongue=True)
    elif kind == "frown":
        if amt < 0.05:
            line(lambda u: -0.022 * u * u + 0.004)
            creases(False)
        else:
            o = 0.06 * amt
            poly = [(-w + 2 * w * i / 48, MZ - 0.03 - 0.02 * (-1 + 2 * i / 48) ** 2) for i in range(49)]
            poly += [(w * math.cos(math.pi * i / 48), MZ - 0.03 + o * math.sin(math.pi * i / 48) ** 0.8) for i in range(1, 48)]
            poly = poly[::-1]
            open_mouth(poly, teeth_top=True, tongue=False)
    elif kind == "gritted":
        hh = 0.03 + 0.02 * amt
        rr = 0.02
        poly = []
        for cx, cz, a0 in ((w - rr, MZ - rr, 0), (-w + rr, MZ - rr, 90), (-w + rr, MZ - 2 * hh + rr, 180), (w - rr, MZ - 2 * hh + rr, 270)):
            for k in range(8):
                a = math.radians(a0 + 90 * k / 7)
                poly.append((cx + rr * math.cos(a), cz + rr * math.sin(a)))
        open_mouth(poly, teeth_both=True, tongue=False)
        creases(False)
    elif kind == "wobbly":
        o = 0.05 * amt
        poly = [(-w + 2 * w * i / 48, MZ - 0.01 + 0.012 * math.sin((-1 + 2 * i / 48) * math.pi * 2)) for i in range(49)]
        poly += [(w * math.cos(math.pi * i / 48), MZ - 0.012 - o * math.sin(math.pi * i / 48) ** 0.8) for i in range(1, 48)]
        open_mouth(poly, teeth_top=True, tongue=False)
    elif kind == "wavy":
        line(lambda u: 0.012 * math.sin(u * math.pi * 2), w=w * 0.8)
    elif kind == "press":
        line(lambda u: -0.008 * u * u, r=0.013)
        sphere((0, front_y(0, MZ - 0.075) - 0.02, MZ - 0.075), (0.12, 0.06, 0.05), SKIN)   # pushed-up chin
    elif kind == "smirk":
        line(lambda u: 0.04 * max(u, 0) ** 2 - 0.006 * (1 - u) / 2)
        cx = MW + 0.012
        curve([(cx, front_y(cx, MZ + 0.04) - 0.009, MZ + 0.04), (cx + 0.016, front_y(cx + 0.016, MZ + 0.06) - 0.008, MZ + 0.06)], 0.006, LIP, bezier=False)


def drop(loc, r, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
    for v in bm.verts:
        if v.co.z > 0:
            f = (1 - v.co.z) ** 0.9; v.co.x *= f; v.co.y *= f; v.co.z *= 1.9
    me = bpy.data.meshes.new("drop"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("drop", me); sc.collection.objects.link(o); me.materials.append(WATER)
    o.location = loc; o.scale = (r, r, r); o.rotation_euler = rot
    shade(o)


def heart(loc, s, m):
    bm = bmesh.new()
    pts = []
    for i in range(48):
        t = 2 * math.pi * i / 48
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(bm.verts.new((x / 17 * s, 0, z / 17 * s)))
    bm.faces.new(pts)
    me = bpy.data.meshes.new("heart"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("heart", me); sc.collection.objects.link(o); me.materials.append(m)
    o.location = loc
    so = o.modifiers.new("s", "SOLIDIFY"); so.thickness = s * 0.5; so.offset = 0
    b = o.modifiers.new("b", "BEVEL"); b.width = s * 0.2; b.segments = 4
    subsurf(o, 1); shade(o)


def eyelid(x, side, up, tilt, low):
    for which, h in (("up", up), ("low", low)):
        if (which == "up" and h >= 0.99) or (which == "low" and h <= -0.99):
            continue
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
        no = Vector((-tilt * side, 0, 1)).normalized() if which == "up" else Vector((tilt * side * 0.3, 0, -1)).normalized()
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, h), plane_no=no, clear_inner=True)
        me = bpy.data.meshes.new("lid"); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("lid", me); sc.collection.objects.link(o)
        me.materials.append(SKIN); me.materials.append(LASH)
        o.location = (x, -0.47, 1.86); o.scale = (0.128, 0.09, 0.138)
        so = o.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.12; so.offset = 1; so.use_rim = True; so.material_offset_rim = 1
        subsurf(o, 1); shade(o)


def brow(side, lift, ang, arch):
    """A smooth brow in v1's place (in front of the forehead, above the glasses)."""
    xi, xo = side * 0.07, side * 0.3
    zb = 2.06 + lift
    zi, zo = zb + ang, zb - ang * 0.4
    pts = [(xi, -0.565, zi), ((xi + xo) / 2, -0.575, (zi + zo) / 2 + arch + 0.012), (xo, -0.52, zo)]
    curve(pts, 1.0, BROW, radii=[0.034, 0.032, 0.022])


def build_face(e, talk):
    for side in (-1, 1):
        x = side * 0.2
        sphere((x, -0.47, 1.86), (0.12, 0.08, 0.13), eye_mat(f"eye{side}", e["gaze"], e.get("ps", 1.0), e.get("sparkle", False)), seg=64)
        eyelid(x, side, e["up"], e["tilt"], e["low"])
        b = e.get("brow_r", e["brow"]) if side > 0 else e["brow"]
        brow(side, *b)
    build_mouth(*e["mouth"], talk=talk)
    ex = e.get("extras", [])
    if "blush" in ex:
        for side in (-1, 1):
            x, z = side * 0.3, 1.66
            sphere((x, front_y(x, z) - 0.004, z), (0.085, 0.02, 0.045), BLUSH, rot=(0, 0, side * -0.55))
    if "sweat" in ex:
        drop((0.66, -0.25, 2.05), 0.06, rot=(0, math.radians(-15), 0))
    if "anger" in ex:
        c = Vector((0.4, -0.45, 2.25)); s = 0.11
        for k in range(4):
            a = math.radians(45 + 90 * k)
            d = Vector((math.cos(a), 0, math.sin(a))); pp = Vector((-d.z, 0, d.x))
            curve([c + d * s * 0.35 + pp * s * 0.45, c + d * s * 0.75, c + d * s * 0.35 - pp * s * 0.45], s * 0.12, ANGER)
    if "tears" in ex:
        for side in (-1, 1):
            x = side * 0.22
            pts = [(x + side * 0.02 * k, front_y(x + side * 0.02 * k, z) - 0.02, z) for k, z in enumerate((1.76, 1.68, 1.58, 1.5))]
            curve(pts, 1.0, WATER, radii=[0.022, 0.028, 0.032, 0.035])
            drop((x + side * 0.1, pts[-1][1], 1.4), 0.035)
    if "hearts" in ex:
        red = mat("heart", "#FF3B5C", 0.3, coat=0.8)
        heart((0.62, -0.4, 2.15), 0.07, red)
        heart((-0.66, -0.35, 2.3), 0.05, red)


# ------------------------------------------------------------------ glasses
def lens_outline(style, s, N=64):
    pts = []
    for i in range(N):
        t = 2 * math.pi * i / N
        c, si = math.cos(t), math.sin(t)
        if style in ("round_gold", "round_silver"):
            x, z = 0.165 * c, 0.165 * si
        elif style == "square_black":
            x = 0.175 * math.copysign(abs(c) ** 0.4, c); z = 0.135 * math.copysign(abs(si) ** 0.4, si)
        elif style == "aviator":
            # teardrop: flat, wide brow line; deep rounded drop that sags toward the nose side's outer corner
            x = 0.18 * c
            z = 0.12 * si if si > 0 else 0.19 * si * (0.75 + 0.25 * (c * s))
            if si > 0:
                z = 0.12 * si ** 0.5 * (1 - 0.15 * abs(c))
        elif style == "browline":
            x = 0.172 * math.copysign(abs(c) ** 0.62, c); z = 0.14 * math.copysign(abs(si) ** 0.62, si)
        else:
            x, z = 0.165 * c, 0.165 * si
        pts.append((x, z))
    return pts


def build_glasses(style):
    frame = {"round_gold": GOLD, "round_silver": SILVER, "square_black": ACETATE, "aviator": GOLD, "browline": SILVER}[style]
    thick = {"round_gold": 0.02, "round_silver": 0.012, "square_black": 0.03, "aviator": 0.013, "browline": 0.012}[style]
    gy, gz = -0.6, 1.86
    for s in (-1, 1):
        x0 = s * 0.2
        ol = lens_outline(style, s)
        curve([(x0 + x, gy, gz + z) for x, z in ol], thick, frame, closed=True, bezier=False)
        if style == "browline":
            top = sorted([(x0 + x, gy - 0.005, gz + z) for x, z in ol if z > 0.03], key=lambda p: p[0])
            curve(top, 0.032, ACETATE, bezier=False)
        bm = bmesh.new()
        vs = [bm.verts.new((x0 + x * 0.97, gy, gz + z * 0.97)) for x, z in ol]
        bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        for v in bm.verts:
            v.co.y = gy - 0.02 * max(0.0, 1 - ((v.co.x - x0) ** 2 + (v.co.z - gz) ** 2) / 0.03)
        me = bpy.data.meshes.new("lens"); bm.to_mesh(me); bm.free()
        lo = bpy.data.objects.new("lens", me); sc.collection.objects.link(lo); me.materials.append(GLASS); shade(lo)
        so = lo.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.008
        xe = max(abs(x) for x, z in ol)
        capsule((s * (0.2 + xe), gy, gz + 0.02), (s * 0.5, -0.25, gz + 0.06), 0.02 if style == "square_black" else 0.013, frame)
    if style == "aviator":
        curve([(-0.06, gy - 0.01, gz + 0.1), (0, gy - 0.025, gz + 0.105), (0.06, gy - 0.01, gz + 0.1)], 0.011, frame)
    curve([(-0.04, gy - 0.01, gz + 0.02), (0, gy - 0.03, gz + 0.04), (0.04, gy - 0.01, gz + 0.02)], max(thick, 0.014), frame)


# ------------------------------------------------------------------ outfits
OUTFITS = {
    "hoodie_blue":  dict(body="#1F4FF0", trim="#1636B0", sleeve="#1F4FF0", hood=True, logo="#F7F5F0", strings=True),
    "hoodie_black": dict(body="#17181C", trim="#0C0C0F", sleeve="#17181C", hood=True, logo="#E8B84A", strings=True),
    "hoodie_gold":  dict(body="#E7A92C", trim="#C88A16", sleeve="#E7A92C", hood=True, logo="#1F4FF0", strings=True),
    "tee_white":    dict(body="#F4F2EC", trim="#DAD6CC", sleeve="#F4F2EC", hood=False, logo="#1F4FF0", strings=False, short=True),
    "varsity":      dict(body="#14286E", trim="#E7A92C", sleeve="#F4F2EC", hood=False, logo="#E7A92C", strings=False, collar=True),
    "suit":         dict(body="#22252B", trim="#14161A", sleeve="#22252B", hood=False, logo=None, strings=False, suit=True),
}


def build_outfit(name):
    o = OUTFITS[name]
    body = mat("body", o["body"], 0.8, sheen=0.5)
    trim = mat("trim", o["trim"], 0.85, sheen=0.4)
    sleeve = mat("sleeve", o["sleeve"], 0.8, sheen=0.5)
    torso = sphere((0, 0, 0.95), (0.58, 0.44, 0.56), body); subsurf(torso, 1)
    if o.get("hood"):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.32, minor_radius=0.1, location=(0, 0.02, 1.38))
        t = bpy.context.object; t.data.materials.append(trim); shade(t); subsurf(t, 1)
        sphere((0, -0.38, 0.66), (0.3, 0.06, 0.13), trim)
    else:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.27, minor_radius=0.055, location=(0, -0.02, 1.4))
        t = bpy.context.object; t.data.materials.append(trim); shade(t); subsurf(t, 1)
    if o.get("strings"):
        for s in (-1, 1):
            capsule((s * 0.09, -0.4, 1.3), (s * 0.1, -0.47, 1.05), 0.014, WHITE)
    if o.get("collar"):                                         # varsity: striped knit hem + snaps
        bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.06, location=(0, 0, 0.5))
        t = bpy.context.object; t.scale = (1.0, 0.78, 1); t.data.materials.append(trim); shade(t); subsurf(t, 1)
        for z in (1.2, 1.05, 0.9, 0.75):
            sphere((0, front_y_body(z) - 0.005, z), (0.022, 0.012, 0.022), GOLD)
    if o.get("suit"):                                           # shirt, lapels and a gold tie
        sphere((0, -0.36, 1.12), (0.16, 0.08, 0.2), WHITE)
        for s in (-1, 1):
            curve([(s * 0.06, -0.42, 1.36), (s * 0.18, -0.44, 1.12), (s * 0.13, -0.47, 0.88)], 0.03, trim)
        curve([(0, -0.445, 1.32), (0, -0.46, 1.12), (0, -0.465, 0.95)], 1.0, GOLD, radii=[0.025, 0.04, 0.03])
    if o.get("logo"):                                           # the G mark, white dots (as in v1)
        lm = mat("logo", o["logo"], 0.35)
        for i in range(10):
            a = math.radians(40 + i * 28)
            sphere((0.1 * math.cos(a), -0.455, 1.0 + 0.1 * math.sin(a)), (0.016, 0.01, 0.016), lm)
        sphere((0.02, -0.46, 1.0), (0.016, 0.01, 0.016), GOLD)
    return sleeve, trim, o.get("short", False)


def front_y_body(z):
    k = 1 - ((z - 0.95) / 0.56) ** 2
    return -0.44 * math.sqrt(max(k, 0))


# ------------------------------------------------------------------ arms and poses (smooth, no claws)
S = 0.55
POSES = {
    "rest":      [((-S, 0, 1.18), (-0.66, -0.04, 0.88), (-0.63, -0.09, 0.62), "open"), ((S, 0, 1.18), (0.66, -0.04, 0.88), (0.63, -0.09, 0.62), "open")],
    "wave":      [((-S, 0, 1.18), (-0.66, -0.04, 0.88), (-0.63, -0.09, 0.62), "open"), ((S, 0, 1.18), (0.85, -0.05, 1.4), (0.92, -0.1, 1.76), "open")],
    "point":     [((-S, 0, 1.18), (-0.66, -0.04, 0.88), (-0.63, -0.09, 0.62), "open"), ((S, 0, 1.18), (0.92, -0.2, 1.2), (1.26, -0.36, 1.28), "point")],
    "point_up":  [((-S, 0, 1.18), (-0.66, -0.04, 0.88), (-0.63, -0.09, 0.62), "open"), ((S, 0, 1.18), (0.8, -0.12, 1.42), (0.84, -0.18, 1.8), "point")],
    "arms_up":   [((-S, 0, 1.18), (-0.84, -0.05, 1.44), (-0.9, -0.1, 1.8), "open"), ((S, 0, 1.18), (0.84, -0.05, 1.44), (0.9, -0.1, 1.8), "open")],
    "thumbs_up": [((-S, 0, 1.18), (-0.66, -0.04, 0.88), (-0.63, -0.09, 0.62), "open"), ((S, 0, 1.18), (0.78, -0.3, 0.98), (0.7, -0.55, 1.2), "thumb")],
    "shrug":     [((-S, 0, 1.18), (-0.82, -0.1, 0.96), (-1.02, -0.22, 1.14), "open"), ((S, 0, 1.18), (0.82, -0.1, 0.96), (1.02, -0.22, 1.14), "open")],
    "think":     [((-S, 0, 1.18), (-0.55, -0.3, 0.9), (-0.14, -0.46, 0.98), "open"), ((S, 0, 1.18), (0.66, -0.32, 1.0), (0.24, -0.64, 1.34), "fist")],
    "point_left": [((-S, 0, 1.18), (-0.92, -0.2, 1.2), (-1.26, -0.36, 1.28), "point"), ((S, 0, 1.18), (0.66, -0.04, 0.88), (0.63, -0.09, 0.62), "open")],
    "point_both_up": [((-S, 0, 1.18), (-0.8, -0.12, 1.42), (-0.84, -0.18, 1.8), "point"), ((S, 0, 1.18), (0.8, -0.12, 1.42), (0.84, -0.18, 1.8), "point")],
    "explain":   [((-S, 0, 1.18), (-0.7, -0.25, 0.95), (-0.62, -0.55, 1.08), "open"), ((S, 0, 1.18), (0.7, -0.25, 0.95), (0.62, -0.55, 1.08), "open")],
    "facepalm":  [((-S, 0, 1.18), (-0.66, -0.04, 0.88), (-0.63, -0.09, 0.62), "open"), ((S, 0, 1.18), (0.6, -0.38, 1.3), (0.12, -0.7, 1.82), "open")],
}


def hand(h, d, kind, side):
    sphere(tuple(h + d * 0.08), (0.12, 0.1, 0.12), SKIN, seg=40)                # smooth mitten paw, no claws
    if kind == "point":
        # index finger from the thumb side of the paw, thumb tucked in front: reads as pointing, never one middle finger
        inward = Vector((-side, 0, 0))
        perp = (inward - d * inward.dot(d)).normalized()
        base = h + d * 0.12 + perp * 0.06 + Vector((0, -0.04, 0))
        limb(base, base + d * 0.2, 0.034, 0.031, SKIN)
        limb(h + d * 0.05 + perp * 0.07 + Vector((0, -0.09, 0)), h + d * 0.02 + perp * 0.0 + Vector((0, -0.11, 0)), 0.03, 0.028, SKIN)
    elif kind == "thumb":
        limb(h + d * 0.05 + Vector((0, -0.02, 0.08)), h + d * 0.03 + Vector((0, -0.04, 0.22)), 0.038, 0.035, SKIN)
    elif kind == "open":
        limb(h + d * 0.04 + Vector((side * -0.08, -0.05, 0.0)), h + d * 0.1 + Vector((side * -0.11, -0.07, 0.03)), 0.034, 0.03, SKIN)


def build_arms(pose, sleeve, trim, short):
    for side, (sh, el, hd, kind) in zip((-1, 1), POSES.get({"talk": "rest", "shock": "arms_up"}.get(pose, pose), POSES["rest"])):
        sh, el, hd = Vector(sh), Vector(el), Vector(hd)
        if short:                                                   # t-shirt: short sleeve, skin forearm
            mid = sh.lerp(el, 0.7)
            limb(sh, mid, 0.125, 0.115, sleeve)
            limb(mid, el, 0.09, 0.085, SKIN)
            limb(el, hd, 0.085, 0.08, SKIN)
        else:
            limb(sh, el, 0.12, 0.11, sleeve)
            limb(el, hd, 0.11, 0.1, sleeve)
            d = (hd - el).normalized()
            bpy.ops.mesh.primitive_torus_add(major_radius=0.105, minor_radius=0.032, location=hd - d * 0.02)
            c = bpy.context.object; c.rotation_mode = "QUATERNION"; c.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
            c.data.materials.append(trim); shade(c); subsurf(c, 1)
        hand(hd, (hd - el).normalized(), kind, side)


# ------------------------------------------------------------------ props
def build_pen():
    a = Vector((-0.05, front_y(-0.05, MZ - 0.03) - 0.03, MZ - 0.03))
    d = Vector((1, 0.12, 0.18)).normalized()
    b = a + d * 0.55
    pen = mat("pen", "#10131A", 0.25, coat=0.8)
    curve([a - d * 0.06, a + d * 0.25, b], 0.026, pen)
    bpy.ops.mesh.primitive_cone_add(radius1=0.026, radius2=0.004, depth=0.09, location=a - d * 0.105)
    c = bpy.context.object; c.rotation_mode = "QUATERNION"; c.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(d)
    c.data.materials.append(GOLD); shade(c)
    curve([b - d * 0.15 + Vector((0, -0.03, 0)), b - d * 0.02 + Vector((0, -0.03, 0))], 0.008, GOLD, bezier=False)
    sphere(tuple(b), (0.028, 0.028, 0.028), GOLD)


# ------------------------------------------------------------------ assemble
e = SPEC.get("expr", "neutral")
e = dict(EXPR[e]) if isinstance(e, str) else e
hair = SPEC.get("hair", "classic")

sphere(H, tuple(HR), SCALE_D)
sphere((0, -0.16, 1.68), (0.5, 0.42, 0.47), SKIN)
sphere((0, -0.5, 1.56), (0.24, 0.2, 0.17), SKIN)
sphere((0, -0.69, 1.6), (0.085, 0.07, 0.065), NOSE)
sphere((-0.02, -0.745, 1.625), (0.022, 0.012, 0.014), WHITE)
HAIR[hair]()
for s in (-1, 1):
    sphere((s * 0.55, 0.02, 2.02), (0.14, 0.08, 0.15), SCALE, rot=(0, 0, s * 0.3))
    sphere((s * 0.555, -0.035, 2.02), (0.08, 0.04, 0.09), EAR_IN, rot=(0, 0, s * 0.3))
build_face(e, SPEC.get("mouth_open"))
g = SPEC.get("glasses", "round_gold")
if g and g != "none":
    build_glasses(g)
if "pen" in SPEC.get("props", e.get("props", [])):
    build_pen()

sleeve, trim, short = build_outfit(SPEC.get("outfit", "hoodie_blue"))
for s in (-1, 1):                                                       # shoulder scales (v1)
    plate((s * 0.4, -0.08, 1.32), (s * 0.6, -0.4, 0.7), 0.2, SCALE)
build_arms(SPEC.get("pose", "rest"), sleeve, trim, short)
for s in (-1, 1):
    capsule((s * 0.2, 0, 0.5), (s * 0.2, -0.02, 0.2), 0.12, LEG)
    sphere((s * 0.21, -0.08, 0.1), (0.17, 0.25, 0.11), SHOE)
    sphere((s * 0.21, -0.08, 0.035), (0.175, 0.255, 0.035), GOLD)

# stage / transparent
target = bpy.data.objects.new("target", None); sc.collection.objects.link(target)
if SPEC.get("bg", "stage") == "stage":
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); bpy.context.object.data.materials.append(FLOOR)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 6, 10), rotation=(math.pi / 2, 0, 0)); bpy.context.object.data.materials.append(FLOOR)
else:
    sc.render.film_transparent = True
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); bpy.context.object.is_shadow_catcher = True


def light(name, loc, energy, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc; sc.collection.objects.link(o)
    tr = o.constraints.new("TRACK_TO"); tr.target = target


light("key", (-3.2, -4.2, 4.2), 650, 3.5, (1, 0.96, 0.9))
light("fill", (4, -3.5, 2.2), 160, 4, (0.85, 0.9, 1))
light("rim", (1.5, 3.5, 3.5), 500, 2.5, (1, 0.95, 0.85))
world = bpy.data.worlds.new("w"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.74, 0.8, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
sc.world = world

cam = bpy.data.cameras.new("cam")
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co)
if SPEC.get("framing", "full") == "bust":
    cam.lens = 105; target.location = (0, 0, 1.74); co.location = (0.45, -6.2, 1.8)
    if hair in ("high_top", "afro", "frohawk"):
        cam.lens = 90; target.location = (0, 0, 1.84)
else:
    cam.lens = 80; target.location = (0, 0, 1.2); co.location = (0.5, -7.0, 1.55)
    if hair in ("high_top", "afro", "frohawk"):
        cam.lens = 72; target.location = (0, 0, 1.32)
co.location = Matrix.Rotation(math.radians(SPEC.get("yaw", 0)), 3, "Z") @ co.location
tr = co.constraints.new("TRACK_TO"); tr.target = target
sc.camera = co

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SPEC.get("samples", 64)
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = SPEC.get("size", (900, 1000))
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Punchy"
sc.render.filepath = OUT
bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

rx, ry = sc.render.resolution_x, sc.render.resolution_y
pts = []
for i in range(24):                      # the head with its hair and ears: where nothing may cover him
    for j in range(12):
        a, b = 2 * math.pi * i / 24, math.pi * (j / 11 - 0.5)
        pts.append(H + Vector((math.cos(b) * math.sin(a) * 0.72, -math.cos(b) * math.cos(a) * 0.78, math.sin(b) * 0.62 + 0.04)))
uv = [world_to_camera_view(sc, co, p) for p in pts]
xs, ys = [u.x * rx for u in uv], [(1 - u.y) * ry for u in uv]
with open(OUT + ".json", "w") as fh:
    json.dump({"head": [min(xs), min(ys), max(xs), max(ys)]}, fh)
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
