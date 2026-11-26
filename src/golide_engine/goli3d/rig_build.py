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


# owner 2026-11-26 ("wide open eyes staring at nothing, his eyes and lids have no stance"): a person talking to the
# camera has the upper lid resting over the top of the eye, softer still when he looks down, and the lower lid lifts
# when he smiles; the fully open eye is for surprise only
def _lid_set(up, low, part):
    for side in (-1, 1):
        eyelid(side * 0.2, side, up, e["tilt"], low)
    tag(part)


_lid_set(0.62, -1.0, "lid_relax")
_lid_set(0.42, -1.0, "lid_soft")
_lid_set(0.55, -0.55, "lid_smile")
_lid_set(0.78, -1.0, "lid_bright")

# brows that move (owner 2026-11-26): the face's own brows are the neutral pair; raised, soft, one up (thinking) and
# concerned (inner ends up) are swaps, all inside the forehead band
for _o in sc.objects:
    if _o.get("part") == "face" and getattr(_o.data, "materials", None) and _o.data.materials[0] and _o.data.materials[0].name.startswith("brow"):
        _o["part"] = "brow_n"
for _name, _l, _r in (("up", (0.035, 0.0, 0.02), (0.035, 0.0, 0.02)), ("soft", (-0.012, 0.0, 0.006), (-0.012, 0.0, 0.006)),
                      ("think", (0.0, 0.0, 0.01), (0.06, 0.0, 0.03)), ("concern", (0.012, 0.03, 0.0), (0.012, 0.03, 0.0))):
    brow(-1, *_l)
    brow(1, *_r)
    tag("brow_" + _name)

_STYLES = ["round_gold", "aviator", "browline", "square_black", "round_silver"]
for _g in _STYLES:
    build_glasses(_g)
    tag("glasses_" + _g)

# glasses in his hand (owner 2026-11-26: "takes off his glasses"): a second pair of each style, built at his right paw
# and skinned to it; the player swaps the pair on his face for the pair in his paw
_hand_r = _V(POSES["rest"][1][2])
for _g in _STYLES:
    _before = set(sc.objects)
    build_glasses(_g)
    for _o in set(sc.objects) - _before:
        _o.location += _hand_r - _V((0, -0.62, 1.86)) + _V((0.0, -0.12, -0.02))
    tag("held_" + _g)

_sleeve, _trim, _short = build_outfit(SPEC.get("outfit", "royal"))
tag("torso")
for _s in (-1, 1):
    plate((_s * 0.4, -0.08, 1.32), (_s * 0.6, -0.4, 0.7), 0.2, SCALE)
    tag("shoulder_" + _SIDES[_s])
build_arms("rest", _sleeve, _trim, _short)
for _o in sc.objects:
    if "part" not in _o.keys():
        _o["part"] = "arm_" + ("L" if _centre(_o).x < 0 else "R")
# paws that change shape (owner 2026-11-26: real gestures): the open paw's thumb, a pointing finger, a thumbs up and a
# fist are swaps on each paw (the round paw itself stays); the player shows the one the move asks for
for _s, _n in _SIDES.items():
    _sh, _el, _hd = (_V(p) for p in POSES["rest"][0 if _s < 0 else 1][:3])
    _d = (_hd - _el).normalized()
    _palm = _hd + _d * 0.08
    for _o in list(sc.objects):
        if (_o.get("part") == f"arm_{_n}" and _o.type == "MESH" and _o.data.materials and _o.data.materials[0] == SKIN
                and 0.02 < (_centre(_o) - _palm).length < 0.17):
            _o["part"] = f"paw{_n}_open"
    for _kind in ("point", "thumb", "fist"):
        # built as in the sprite pose that shows it (thumbs_up, point_up), then carried into the rest pose's paw frame,
        # so when the move puts the arm where that pose had it, the finger or thumb stands exactly as in the sprites
        _pose = {"thumb": "thumbs_up", "point": "point_up"}.get(_kind)
        if _pose:
            _psh, _pel, _phd = (_V(p) for p in POSES[_pose][1][:3])
            if _s < 0:
                _pel, _phd = _V((-_pel.x, _pel.y, _pel.z)), _V((-_phd.x, _phd.y, _phd.z))
            _pd = (_phd - _pel).normalized()
        else:
            _phd, _pd = _hd, _d
        _before = set(sc.objects)
        hand(_phd, _pd, _kind, _s)
        _new = sorted(set(sc.objects) - _before, key=lambda o: o.name)
        _q = _pd.rotation_difference(_d)
        for _o in _new:
            if (_centre(_o) - (_phd + _pd * 0.08)).length < 0.02:   # the round paw again: already there
                bpy.data.objects.remove(_o, do_unlink=True)
                continue
            _mw = _o.matrix_world.copy()
            _o.matrix_world = Matrix.Translation(_hd) @ _q.to_matrix().to_4x4() @ Matrix.Translation(-_phd) @ _mw
        tag(f"paw{_n}_{_kind}")
        if _kind == "fist":                                # a fist: the round paw alone (an empty swap)
            pass

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

# ------------------------------------------------------------------ soft shading the player cannot compute
# owner 2026-11-26 ("don't make him fade"): Cycles darkens the creases (under the head, the arms against the body,
# between the legs); the player cannot. Bake that ambient occlusion into each part's vertex colours once; the player
# multiplies it in. The eyes, lenses and swap parts are left clean.
if SPEC.get("ao", True):
    sc.cycles.samples = SPEC.get("ao_samples", 24)
    sc.render.bake.target = "VERTEX_COLORS"
    sc.world = sc.world or bpy.data.worlds.new("w")
    for _o in list(sc.objects):
        _part = _o.get("part", "")
        if _o.type != "MESH" or _part.startswith(("eye_", "mouth_", "lid_", "brow_")) or not _o.data.vertices:
            continue
        if any(_m and _m.name == "lens" for _m in _o.data.materials):
            continue
        _o.data.color_attributes.new("ao", "FLOAT_COLOR", "POINT")
        _o.data.color_attributes.active_color = _o.data.color_attributes["ao"]
        bpy.ops.object.select_all(action="DESELECT"); _o.select_set(True); bpy.context.view_layer.objects.active = _o
        bpy.ops.object.bake(type="AO")
        # keep it soft: AO 0 -> 0.45, 1 -> 1 (the player still lights him; this only darkens creases)
        for _c in _o.data.color_attributes["ao"].data:
            _v = 0.45 + 0.55 * _c.color[0]
            _c.color = (_v, _v, _v, 1.0)

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
        # owner 2026-11-26: a real walk needs knees
        f"thigh.{_n}": ((_s * 0.2, 0, 0.5), (_s * 0.2, -0.01, 0.35), "hips"),
        f"shin.{_n}": ((_s * 0.2, -0.01, 0.35), (_s * 0.2, -0.02, 0.17), f"thigh.{_n}"),
        f"foot.{_n}": ((_s * 0.2, -0.02, 0.17), (_s * 0.21, -0.3, 0.06), f"shin.{_n}"),
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
    "leg_L": ["hips", "thigh.L", "shin.L", "foot.L"], "leg_R": ["hips", "thigh.R", "shin.R", "foot.R"],
    "eye_L": ["eye.L"], "eye_R": ["eye.R"],
}


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def _skin(o, part):
    names = (["hand.R"] if part.startswith("held_") else [f"hand.{part[3]}"] if part.startswith("paw")
             else CANDIDATES.get(part, ["head"]))
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


# speed (owner 2026-11-26: the video render): every separate part is a separate draw for the software renderer, so the
# parts that never swap are joined, one mesh per part and material (290 meshes became a few dozen); the swaps
# (mouths, lids, glasses, paws) stay separate so the player can show and hide them
_groups = {}
for _o in list(sc.objects):
    if _o.type != "MESH" or not _o.data.materials:
        continue
    _part = _o.get("part", "head")      # a swap's pieces join within their own swap (they show and hide together)
    _groups.setdefault((_part, _o.data.materials[0].name), []).append(_o)
for (_part, _mn), _objs in _groups.items():
    if len(_objs) < 2:
        continue
    bpy.ops.object.select_all(action="DESELECT")
    for _o in _objs:
        _o.select_set(True)
    bpy.context.view_layer.objects.active = _objs[0]
    bpy.ops.object.join()
    _objs[0]["part"] = _part
# fewer vertices for the software renderer: the dense subdivided shapes are thinned where it cannot be seen
for _o in list(sc.objects):
    if _o.type == "MESH" and len(_o.data.vertices) > 1800:
        _dm = _o.modifiers.new("thin", "DECIMATE"); _dm.ratio = max(0.2, 1800 / len(_o.data.vertices))
        bpy.context.view_layer.objects.active = _o
        bpy.ops.object.modifier_apply(modifier=_dm.name)

SWAPS = {}
for _o in list(sc.objects):
    if _o.type != "MESH":
        continue
    _part = _o.get("part", "head")
    _o.name = f"{_part}__{_o.name}"
    _skin(_o, _part)
    for _key in ("mouth_", "lid_", "brow_", "glasses_", "held_", "pawL_", "pawR_"):
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
                          export_animations=False, export_extras=True, export_yup=True,
                          export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True)
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
