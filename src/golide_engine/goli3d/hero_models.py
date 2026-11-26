"""Hero 3D objects (owner 2026-11-26: "the robot is very stupid ... the lock for anything security ... too limited and
primitive; modify it in a very beautiful way"). Built once in Blender at studio quality, exported one .glb each to
assets/edit/hero/, played in the video by assets/edit/g3d/hero3d.js.

Every model keeps its parts named (the callouts point at them) and has ONE material called "accent": the player
paints it the colour of the thing the line names (a brand's own colour, else the house gold), so the object belongs
to the story. Moving parts are named "mover" (the shackle that opens, the visor that lights, the lid that lifts).

python src/golide_engine/goli3d/hero_models.py '{"out": "assets/edit/hero", "only": ["robot"]}' x
"""
import json
import math
import os
import sys

import bpy  # noqa: I001 - bpy first, then its own modules
import bmesh
from mathutils import Matrix, Vector

SPEC = json.loads(sys.argv[-2]) if len(sys.argv) > 2 and sys.argv[-2].startswith("{") else {}
OUT = SPEC.get("out", "assets/edit/hero")


# ------------------------------------------------------------------ materials
def rgb(h):
    return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5))


def mat(name, color, rough=0.4, metal=0.0, coat=0.0, emit=0.0, alpha=1.0, trans=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb(color), 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
    return m


def materials():
    return dict(
        shell=mat("shell", "#F2F3F5", 0.22, coat=0.8),
        dark=mat("dark", "#1C1F26", 0.35, metal=0.6),
        glass=mat("glass", "#0B0E14", 0.05, coat=1.0),
        chrome=mat("chrome", "#D8DCE2", 0.12, metal=1.0),
        steel=mat("steel", "#9AA1AB", 0.32, metal=1.0),
        gold=mat("gold", "#E8C268", 0.2, metal=1.0),
        accent=mat("accent", "#E8C268", 0.25, metal=0.3, coat=0.5),
        glow=mat("accent_glow", "#4C7DFF", 0.3, emit=6.0),
        rubber=mat("rubber", "#2A2D33", 0.7),
        white=mat("white", "#F4F1EA", 0.5),
        cloud=mat("cloud", "#EEF3FF", 0.6, coat=0.3),
    )


# ------------------------------------------------------------------ shapes
def _finish(o, name, m, bevel=0.0, sub=0, smooth=True):
    o.name = name
    o.data.materials.clear()
    o.data.materials.append(m)
    if bevel:
        bv = o.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 4; bv.limit_method = "ANGLE"
    if sub:
        sb = o.modifiers.new("sub", "SUBSURF"); sb.levels = sb.render_levels = sub
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def rbox(name, loc, size, m, bevel=0.04, sub=0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    return _finish(o, name, m, bevel=bevel, sub=sub, smooth=bevel > 0)


def ball(name, loc, scale, m, seg=48, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.transform_apply(scale=True)
    return _finish(o, name, m)


def tube(name, loc, r, depth, m, rot=(0, 0, 0), bevel=0.01, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    return _finish(o, name, m, bevel=bevel)


def ring(name, loc, R, r, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=64, minor_segments=24)
    return _finish(bpy.context.object, name, m)


def capsule(name, a, b, r, m):
    a, b = Vector(a), Vector(b)
    d = b - a
    o = tube(name, tuple((a + b) / 2), r, d.length, m, bevel=0)
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(rotation=True)
    for p_ in (a, b):
        ball(name + "_end", tuple(p_), (r, r, r), m, seg=32)
    return o


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def export(name):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{name}.glb"), export_format="GLB", export_apply=True,
                              export_yup=True, export_extras=True)
    print("hero", name, len([o for o in bpy.context.scene.objects if o.type == "MESH"]), "parts")


# ------------------------------------------------------------------ the objects (1 unit = the object's height scale)
def robot(M):
    """A modern humanoid robot: glossy white shell, a black glass face with two lit eyes (accent glow), a chest light,
    jointed arms with three-fingered hands, legs on feet. Parts: head, visor, eyes, torso, chest_light, arms, hands."""
    rbox("head", (0, 0, 1.64), (0.5, 0.44, 0.42), M["shell"], bevel=0.16, sub=2)
    rbox("visor", (0, -0.2, 1.65), (0.42, 0.06, 0.24), M["glass"], bevel=0.08, sub=2)
    for s in (-1, 1):
        ring("ear_ring", (s * 0.265, 0, 1.64), 0.07, 0.012, M["accent"], rot=(0, math.pi / 2, 0))
    for s in (-1, 1):
        ball("eye", (s * 0.09, -0.235, 1.66), (0.045, 0.012, 0.028), M["glow"])
        ball("ear", (s * 0.255, 0, 1.64), (0.05, 0.1, 0.1), M["dark"])
    tube("antenna", (0, 0, 1.91), 0.008, 0.12, M["chrome"])
    ball("antenna_tip", (0, 0, 1.98), (0.024,) * 3, M["glow"])
    tube("neck", (0, 0, 1.4), 0.06, 0.12, M["dark"])
    rbox("torso", (0, 0, 1.08), (0.5, 0.32, 0.52), M["shell"], bevel=0.14, sub=2)
    rbox("chest_panel", (0, -0.155, 1.13), (0.26, 0.03, 0.16), M["glass"], bevel=0.03, sub=1)
    rbox("chest_light", (0, -0.168, 1.13), (0.16, 0.01, 0.035), M["glow"], bevel=0.005)
    rbox("waist", (0, 0, 0.78), (0.32, 0.24, 0.1), M["dark"], bevel=0.04)
    rbox("hips", (0, 0, 0.68), (0.4, 0.27, 0.16), M["shell"], bevel=0.07, sub=2)
    rbox("accent_band", (0, 0, 0.98), (0.505, 0.325, 0.03), M["accent"], bevel=0.01)
    for s in (-1, 1):
        rbox("chest_stripe", (s * 0.19, -0.16, 1.2), (0.035, 0.02, 0.2), M["accent"], bevel=0.008)
    for s in (-1, 1):
        ball("shoulder", (s * 0.31, 0, 1.25), (0.09,) * 3, M["dark"])
        capsule("upper_arm", (s * 0.34, 0, 1.2), (s * 0.4, -0.04, 0.95), 0.065, M["shell"])
        ball("elbow", (s * 0.4, -0.04, 0.95), (0.06,) * 3, M["dark"])
        capsule("forearm", (s * 0.4, -0.04, 0.95), (s * 0.38, -0.16, 0.74), 0.058, M["shell"])
        ball("hand", (s * 0.375, -0.18, 0.7), (0.055, 0.05, 0.06), M["dark"])
        for f in (-1, 0, 1):
            capsule("finger", (s * 0.375 + f * 0.022, -0.2, 0.67), (s * 0.375 + f * 0.026, -0.23, 0.6), 0.012, M["dark"])
        capsule("thigh", (s * 0.11, 0, 0.62), (s * 0.12, 0, 0.36), 0.075, M["shell"])
        ball("knee", (s * 0.12, -0.01, 0.35), (0.065,) * 3, M["dark"])
        capsule("shin", (s * 0.12, 0, 0.34), (s * 0.12, 0, 0.1), 0.068, M["shell"])
        rbox("foot", (s * 0.12, -0.05, 0.045), (0.13, 0.24, 0.08), M["dark"], bevel=0.035, sub=1)


def padlock(M):
    """A heavy padlock: the body in the accent colour (the brand's), a chrome shackle (the mover: it lifts to open), a
    keyhole, a chrome trim. Parts: body, shackle, keyhole."""
    rbox("body", (0, 0, 0.42), (0.62, 0.26, 0.52), M["accent"], bevel=0.09, sub=2)
    rbox("trim", (0, 0, 0.42), (0.64, 0.24, 0.05), M["chrome"], bevel=0.02)
    tube("keyhole_ring", (0, -0.132, 0.38), 0.065, 0.02, M["chrome"], rot=(math.pi / 2, 0, 0))
    tube("keyhole", (0, -0.14, 0.395), 0.028, 0.02, M["glass"], rot=(math.pi / 2, 0, 0))
    rbox("keyhole_slot", (0, -0.14, 0.34), (0.022, 0.02, 0.08), M["glass"], bevel=0.005)
    # the shackle: a half ring on two legs, one leg longer (it stays in the body when it opens)
    sh = ring("mover_shackle", (0, 0, 0.8), 0.2, 0.05, M["chrome"], rot=(math.pi / 2, 0, 0))
    bpy.context.view_layer.objects.active = sh
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bm = bmesh.new(); bm.from_mesh(sh.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.002], context="VERTS")    # keep the arch only
    bm.to_mesh(sh.data); bm.free()
    for s in (-1, 1):
        tube("mover_leg", (s * 0.2, 0, 0.6), 0.05, 0.42, M["chrome"])     # reaches deep into the body: open, it still sits in it


def shield(M):
    """A security shield: a curved accent-coloured plate with a chrome rim and a glowing check mark. Parts: shield, rim,
    check."""
    bm = bmesh.new()
    outline = []
    for i in range(32):                       # the shield's outline: flat top, curved sides to a point
        t = i / 31
        x = 0.42 * (1 - t ** 2.2)
        z = 0.95 - t * 0.95
        outline.append((x, z))
    shape = [(-x, z) for x, z in outline] + [(x, z) for x, z in reversed(outline)]
    vs = [bm.verts.new((x, 0, z)) for x, z in shape]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += 0.12
    for v in bm.verts:                         # a gentle curve across
        v.co.y -= 0.12 * (1 - (v.co.x / 0.42) ** 2)
    me = bpy.data.meshes.new("shield"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("shield", me); bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    _finish(o, "shield", M["accent"], bevel=0.03, sub=1)
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.ops.object.duplicate(); r = bpy.context.object
    r.scale = (1.07, 1.0, 1.05); r.location = (0, 0.05, -0.015)    # just behind it: only the edge shows
    _finish(r, "rim", M["chrome"], bevel=0.0)
    for a, b in (((-0.17, -0.2, 0.5), (-0.04, -0.2, 0.36)), ((-0.04, -0.2, 0.36), (0.2, -0.2, 0.66))):
        capsule("mover_check", a, b, 0.045, M["glow"])


def cloud(M):
    """A cloud: soft overlapping puffs with a glowing accent line under it (data going up). Parts: cloud, link."""
    for (x, z, r) in ((-0.38, 0.42, 0.24), (-0.12, 0.55, 0.32), (0.2, 0.52, 0.28), (0.42, 0.4, 0.2), (0.02, 0.36, 0.26)):
        ball("cloud", (x, 0, z), (r, r * 0.8, r), M["cloud"])
    rbox("base", (0.02, 0, 0.26), (0.92, 0.32, 0.12), M["cloud"], bevel=0.06, sub=2)
    for x in (-0.24, 0.0, 0.24):
        tube("mover_link", (x, 0, 0.05), 0.012, 0.3, M["glow"], bevel=0)
        ball("link_dot", (x, 0, -0.12), (0.035,) * 3, M["accent"])


def database(M):
    """A database: three stacked discs with lit seams and an accent top. Parts: disc, seam, top."""
    for i in range(3):
        z = 0.15 + i * 0.3
        tube("disc", (0, 0, z), 0.42, 0.24, M["steel"] if i % 2 else M["shell"], bevel=0.03)
        tube("seam", (0, 0, z + 0.13), 0.425, 0.02, M["glow"], bevel=0)
    tube("mover_top", (0, 0, 0.92), 0.42, 0.06, M["accent"], bevel=0.02)
    for i in range(3):
        ball("led", (0.3, -0.29, 0.15 + i * 0.3), (0.02,) * 3, M["glow"])


def brain(M):
    """An AI brain, seen from the side: a clear folded shell (cerebrum, cerebellum, stem) with a network of glowing
    nodes and links inside in the accent colour. Parts: brain, network, nodes."""
    import random
    rnd = random.Random(7)
    o = ball("brain", (0, 0, 0.6), (0.52, 0.36, 0.36), M["shell"], seg=64)
    for (loc, sc_) in (((-0.33, 0, 0.36), (0.22, 0.26, 0.15)),):
        ball("brain_back", loc, sc_, M["shell"], seg=48)
    tube("stem", (-0.16, 0, 0.24), 0.07, 0.26, M["shell"], rot=(0, 0.35, 0))
    for ob in [x for x in bpy.context.scene.objects if x.name.startswith(("brain", "stem"))]:
        d = ob.modifiers.new("folds", "DISPLACE")
        t = bpy.data.textures.new("folds", "MARBLE"); t.noise_scale = 0.09; t.marble_type = "SHARPER"; t.turbulence = 9
        d.texture = t; d.strength = 0.025
        gl = mat("brain_glass", "#DCE6FF", 0.15, coat=0.6, alpha=0.38)
        gl.blend_method = "BLEND" if hasattr(gl, "blend_method") else None
        ob.data.materials.clear(); ob.data.materials.append(gl)
    pts = []
    for _ in range(26):
        while True:
            q = Vector((rnd.uniform(-0.45, 0.45), rnd.uniform(-0.28, 0.28), rnd.uniform(0.32, 0.88)))
            if ((q.x / 0.46) ** 2 + (q.y / 0.3) ** 2 + ((q.z - 0.6) / 0.3) ** 2) < 1:
                break
        pts.append(q)
        ball("nodes", tuple(q), (0.022,) * 3, M["glow"], seg=16)
    for i, q in enumerate(pts):
        near = sorted(pts, key=lambda r: (r - q).length)[1:3]
        for r_ in near:
            capsule("network", tuple(q), tuple(r_), 0.006, M["accent"])


def key(M):
    """A key: a chrome bow with an accent inlay and a cut blade. Parts: bow, blade, teeth."""
    ring("bow", (0, 0, 0.75), 0.17, 0.05, M["chrome"], rot=(math.pi / 2, 0, 0))
    tube("inlay", (0, 0, 0.75), 0.11, 0.04, M["accent"], rot=(math.pi / 2, 0, 0))
    rbox("blade", (0, 0, 0.36), (0.07, 0.04, 0.6), M["chrome"], bevel=0.015)
    for i, h in enumerate((0.08, 0.05, 0.1, 0.06)):
        rbox("teeth", (0.06, 0, 0.12 + i * 0.09), (0.06 + h, 0.04, 0.05), M["chrome"], bevel=0.01)


def globe(M):
    """A globe of light: a clear sphere, meridians and the equator in the accent colour, glowing dots for places.
    Parts: globe, lines, places."""
    ball("globe", (0, 0, 0.5), (0.42,) * 3, M["glass"])
    for k in range(4):
        ring("lines", (0, 0, 0.5), 0.425, 0.006, M["accent"], rot=(math.pi / 2, 0, k * math.pi / 4))
    ring("lines", (0, 0, 0.5), 0.425, 0.006, M["accent"])
    for k in range(14):
        a, b = k * 2.4, (k * 0.37) % 1.2 - 0.6
        ball("places", (0.43 * math.cos(b) * math.cos(a), 0.43 * math.cos(b) * math.sin(a), 0.5 + 0.43 * math.sin(b)), (0.018,) * 3, M["glow"])
    tube("stand", (0, 0, 0.03), 0.18, 0.04, M["dark"], bevel=0.01)


MODELS = {"robot": robot, "padlock": padlock, "shield": shield, "cloud": cloud, "database": database, "brain": brain,
          "key": key, "globe": globe}


if __name__ == "__main__":
    for name in SPEC.get("only") or list(MODELS):
        clear()
        MODELS[name](materials())
        export(name)
