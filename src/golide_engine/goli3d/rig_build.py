"""Goli as ONE rigged 3D character (living-studio plan step 2-4, owner 2026-11-25).

Run inside goli3d/model.py with spec {"rig": true, "out": "goli.glb"}: the head is already built (part "head"); this
builds the rest of him in the rest pose from the same functions (so he looks exactly like the stills), adds a skeleton,
skins every part to it, adds the swap parts the video player shows and hides (nine Rhubarb mouths, half and closed
lids, five glasses), and exports one .glb plus goli-rig.json (bones, swaps, kit colours, sockets).

Weights are computed here, not by Blender's bone heat: every vertex is weighted to the nearest bones of its own part
with a smooth falloff, so the hoodie bends at the elbow and shoulder and nothing tears where parts overlap.
"""
import json as _json
import os as _os

from mathutils import Vector as _V

_OUT = SPEC.get("out", "goli.glb")
_SIDES = {-1: "L", 1: "R"}

def _centre(o):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ _V(c) for c in o.bound_box]
    return sum(pts, _V()) / 8


# ------------------------------------------------------------------ the rest of the body, tagged by part
build_face(e, "X")
for _o in list(sc.objects):
    if "part" not in _o.keys():
        _c = _centre(_o)
        _o["part"] = "mouth_X" if _c.z < 1.6 and abs(_c.x) < 0.3 else "face"
# eyes: the two eyeball spheres turn on their own bones
for _o in sc.objects:
    if _o.get("part") == "face" and _o.type == "MESH" and _o.data.materials and _o.data.materials[0].name.startswith("eye"):
        _o["part"] = "eye_" + ("L" if _centre(_o).x < 0 else "R")

# the other eight mouth shapes, hidden until the voice asks for them
for _v in "ABCDEFGH":
    build_mouth(*e["mouth"], talk=_v)
    tag("mouth_" + _v)


def _lids(amount, part):
    ee = dict(e, up=e["up"] + (-0.92 - e["up"]) * amount, tilt=e["tilt"] * (1 - amount), low=e["low"] + (-1 - e["low"]) * amount)
    for side in (-1, 1):
        eyelid(side * 0.2, side, ee["up"], ee["tilt"], ee["low"])
    tag(part)


# the open lids were built with the face; the half and closed lids are swaps
for _o in sc.objects:
    if _o.get("part") == "face" and _o.name.startswith("lid"):
        _o["part"] = "lid_open"
_lids(0.5, "lid_half")
_lids(1.0, "lid_closed")

_STYLES = ["round_gold", "aviator", "browline", "square_black", "round_silver"]
for _g in _STYLES:
    build_glasses(_g)
    tag("glasses_" + _g)

_sleeve, _trim, _short = build_outfit(SPEC.get("outfit", "royal"))
tag("torso")
for _s in (-1, 1):
    plate((_s * 0.4, -0.08, 1.32), (_s * 0.6, -0.4, 0.7), 0.2, SCALE)
    tag("shoulder_" + _SIDES[_s])
build_arms("rest", _sleeve, _trim, _short)
for _o in sc.objects:
    if "part" not in _o.keys():
        _o["part"] = "arm_" + ("L" if _centre(_o).x < 0 else "R")
for _s in (-1, 1):
    capsule((_s * 0.2, 0, 0.5), (_s * 0.2, -0.02, 0.2), 0.12, LEG)
    sphere((_s * 0.21, -0.08, 0.1), (0.17, 0.25, 0.11), SHOE)
    sphere((_s * 0.21, -0.08, 0.035), (0.175, 0.255, 0.035), GOLD)
    tag("leg_" + _SIDES[_s])

# ------------------------------------------------------------------ everything to plain meshes (curves, modifiers)
bpy.ops.object.select_all(action="DESELECT")
for _o in list(sc.objects):
    if _o.type in ("CURVE", "SURFACE", "META", "FONT"):
        _o.select_set(True)
if bpy.context.selected_objects:
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.convert(target="MESH")
for _o in list(sc.objects):
    if _o.type != "MESH":
        continue
    bpy.context.view_layer.objects.active = _o
    for _m in list(_o.modifiers):
        bpy.ops.object.modifier_apply(modifier=_m.name)

# the eyes are painted by a node setup the .glb cannot carry: bake each eye's paint into a picture (looking straight;
# the eye bones do the looking), and the lenses become see-through glass the player can draw
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 8
for _o in list(sc.objects):
    if _o.type != "MESH" or not _o.get("part", "").startswith("eye_"):
        continue
    _src = _o.data.materials[0]
    _img = bpy.data.images.new(f"{_o['part']}_paint", 512, 512)
    _n = _src.node_tree.nodes.new("ShaderNodeTexImage"); _n.image = _img
    _src.node_tree.nodes.active = _n
    bpy.ops.object.select_all(action="DESELECT"); _o.select_set(True); bpy.context.view_layer.objects.active = _o
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=4)
    _img.pack()
    _m = bpy.data.materials.new(f"{_o['part']}_baked"); _m.use_nodes = True
    _b = _m.node_tree.nodes["Principled BSDF"]
    _t = _m.node_tree.nodes.new("ShaderNodeTexImage"); _t.image = _img
    _m.node_tree.links.new(_t.outputs["Color"], _b.inputs["Base Color"])
    _b.inputs["Roughness"].default_value = 0.12
    _b.inputs["Coat Weight"].default_value = 0.5
    _o.data.materials[0] = _m
_lens = bpy.data.materials.new("lens"); _lens.use_nodes = True
_lb = _lens.node_tree.nodes["Principled BSDF"]
_lb.inputs["Base Color"].default_value = (0.95, 0.97, 1.0, 1); _lb.inputs["Roughness"].default_value = 0.03
_lb.inputs["Alpha"].default_value = 0.12
for _o in sc.objects:
    if _o.type == "MESH":
        for _i, _mm in enumerate(_o.data.materials):
            if _mm and _mm.name.startswith("glass"):
                _o.data.materials[_i] = _lens

for _o in list(sc.objects):
    if _o.type != "MESH":
        continue
    _o.data.transform(_o.matrix_world)          # bake placement into the vertices: the bones do the moving
    _o.matrix_world = Matrix.Identity(4)

# ------------------------------------------------------------------ the skeleton (rest pose = today's "rest")
BONES = {   # name: (head, tail, parent)
    "root": ((0, 0, 0), (0, 0, 0.3), None),
    "hips": ((0, 0, 0.45), (0, 0, 0.8), "root"),
    "spine": ((0, 0, 0.8), (0, 0, 1.15), "hips"),
    "chest": ((0, 0, 1.15), (0, 0, 1.42), "spine"),
    "neck": ((0, 0, 1.42), (0, 0, 1.55), "chest"),
    "head": ((0, 0, 1.55), (0, 0, 2.3), "neck"),
    "jaw": ((0, -0.3, 1.5), (0, -0.62, 1.42), "head"),
}
for _s, _n in _SIDES.items():
    _sh, _el, _hd = (_V(p) for p in POSES["rest"][0 if _s < 0 else 1][:3])
    _d = (_hd - _el).normalized()
    BONES.update({
        f"eye.{_n}": ((_s * 0.2, -0.47, 1.86), (_s * 0.2, -0.62, 1.86), "head"),
        f"shoulder.{_n}": ((_s * 0.18, 0, 1.3), tuple(_sh), "chest"),
        f"upper_arm.{_n}": (tuple(_sh), tuple(_el), f"shoulder.{_n}"),
        f"forearm.{_n}": (tuple(_el), tuple(_hd), f"upper_arm.{_n}"),
        f"hand.{_n}": (tuple(_hd), tuple(_hd + _d * 0.22), f"forearm.{_n}"),
        f"thigh.{_n}": ((_s * 0.2, 0, 0.5), (_s * 0.2, -0.02, 0.22), "hips"),
        f"foot.{_n}": ((_s * 0.2, -0.02, 0.22), (_s * 0.21, -0.3, 0.06), f"thigh.{_n}"),
    })

_ad = bpy.data.armatures.new("goli_rig")
_arm = bpy.data.objects.new("goli_rig", _ad)
sc.collection.objects.link(_arm)
bpy.context.view_layer.objects.active = _arm
bpy.ops.object.mode_set(mode="EDIT")
for _name, (_h, _t, _p) in BONES.items():
    _b = _ad.edit_bones.new(_name)
    _b.head, _b.tail = _h, _t
    if _p:
        _b.parent = _ad.edit_bones[_p]
        _b.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

# which bones each part may follow (rigid parts follow one)
CANDIDATES = {
    "torso": ["hips", "spine", "chest", "neck"],
    "shoulder_L": ["chest", "upper_arm.L"], "shoulder_R": ["chest", "upper_arm.R"],
    "arm_L": ["chest", "shoulder.L", "upper_arm.L", "forearm.L", "hand.L"],
    "arm_R": ["chest", "shoulder.R", "upper_arm.R", "forearm.R", "hand.R"],
    "leg_L": ["hips", "thigh.L", "foot.L"], "leg_R": ["hips", "thigh.R", "foot.R"],
    "eye_L": ["eye.L"], "eye_R": ["eye.R"],
}


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def _skin(o, part):
    names = CANDIDATES.get(part, ["head"])
    groups = {n: o.vertex_groups.new(name=n) for n in names}
    segs = {n: (_V(BONES[n][0]), _V(BONES[n][1])) for n in names}
    for v in o.data.vertices:
        if part.startswith("shoulder_"):      # the shoulder plate moves as one piece, half with the arm: never torn
            groups[names[0]].add([v.index], 0.5, "REPLACE"); groups[names[1]].add([v.index], 0.5, "REPLACE")
            continue
        if len(names) == 1:
            groups[names[0]].add([v.index], 1.0, "REPLACE")
            continue
        ws = {n: 1.0 / (_seg_dist(v.co, *segs[n]) + 0.02) ** 4 for n in names}
        tot = sum(ws.values())
        keep = sorted(ws.items(), key=lambda kv: -kv[1])[:3]      # three bones at most per vertex
        tot = sum(w for _, w in keep)
        for n, w in keep:
            if w / tot > 0.01:
                groups[n].add([v.index], w / tot, "REPLACE")
    mod = o.modifiers.new("rig", "ARMATURE")
    mod.object = _arm
    o.parent = _arm


SWAPS = {}
for _o in list(sc.objects):
    if _o.type != "MESH":
        continue
    _part = _o.get("part", "head")
    _o.name = f"{_part}__{_o.name}"
    _skin(_o, _part)
    for _key in ("mouth_", "lid_", "glasses_"):
        if _part.startswith(_key):
            SWAPS.setdefault(_key.rstrip("_"), {}).setdefault(_part[len(_key):], []).append(_o.name)

# sockets: where held things and the glasses sit
for _name, _bone, _loc in (("socket.hand.L", "hand.L", BONES["hand.L"][0]), ("socket.hand.R", "hand.R", BONES["hand.R"][0]),
                           ("socket.nose", "head", (0, -0.62, 1.86))):
    _em = bpy.data.objects.new(_name, None)
    sc.collection.objects.link(_em)
    _em.parent = _arm
    _em.parent_type = "BONE"
    _em.parent_bone = _bone
    _em.matrix_world = Matrix.Translation(_loc)

bpy.ops.export_scene.gltf(filepath=_OUT, export_format="GLB", export_apply=False, export_skins=True,
                          export_animations=False, export_extras=True, export_yup=True)
_info = {
    "bones": {k: {"head": v[0], "tail": v[1], "parent": v[2]} for k, v in BONES.items()},
    "swaps": SWAPS,
    "defaults": {"mouth": "X", "lid": "open", "glasses": SPEC.get("glasses", "round_gold")},
    "kits": {name: {k: o[k] for k in ("body", "trim", "sleeve") if k in o} for name, o in OUTFITS.items()},
    "materials": {"body": "body", "trim": "trim", "sleeve": "sleeve"},
    "units": "metres, z up in Blender (y up in the .glb)",
}
with open(_os.path.splitext(_OUT)[0] + "-rig.json", "w") as _fh:
    _json.dump(_info, _fh, indent=1)
print("rig exported", _OUT, len([o for o in sc.objects if o.type == "MESH"]), "meshes")
