"""Goli's studio as ONE 3D set (living studio plan step 5, owner 2026-11-26: "the whole office equipment").

Run inside goli3d/studio_model.py with spec {"fmt": "long", "export": "studio.glb"}: the set is already built with its
lights and camera. Every object keeps its own place and pivot and is tagged by piece (room, chair, laptop, mug, mic).
The Cycles light of the room is BAKED into each object's own picture, through the studio's own view transform, so the
player draws the room exactly as the stills look, from any angle the camera moves to, at no lighting cost. The pieces
that move (chair, laptop, mug, mic) are baked where they stand and carry that light with them.

Writes studio.glb plus studio-set.json: the camera (position, lens, sensor, shift), the pieces with their pivots, the
two screens (TV, laptop) by name so the video's pictures go on them, and where Goli sits.
"""
import json as _json
import math as _math
import os as _os

from mathutils import Matrix as _M, Vector as _V

_OUT = SPEC["export"]
_TEX = SPEC.get("tex", 1.0)                  # texture size factor (1 = up to 1024 px for the big pieces)
_DIR = _os.path.splitext(_OUT)[0] + "-bake"
_os.makedirs(_DIR, exist_ok=True)

# -------------------------------------------------------------- plain meshes with their placement baked in
bpy.ops.object.select_all(action="DESELECT")
for _o in list(sc.objects):
    if _o.type in ("CURVE", "SURFACE", "META", "FONT"):
        _o.select_set(True)
if bpy.context.selected_objects:
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.convert(target="MESH")
bpy.context.view_layer.update()
_meshes = [o for o in sc.objects if o.type == "MESH"]
for _o in _meshes:
    bpy.context.view_layer.objects.active = _o
    for _m in list(_o.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=_m.name)
        except RuntimeError:
            _o.modifiers.remove(_m)
for _o in _meshes:                           # unparent (the laptop is built round an empty at its hinge)
    _mw = _o.matrix_world.copy()
    _o.parent = None
    _o.matrix_world = _mw
for _o in _meshes:
    if _o.data.users > 1:
        _o.data = _o.data.copy()
    _o.data.transform(_o.matrix_world)
    _o.matrix_world = _M.Identity(4)

# names: the two screens, and every piece's own prefix
for _o in _meshes:
    _part = _o.get("part", "room")
    _is_screen = any(_m and _m.name == "screen" for _m in _o.data.materials)
    if _is_screen:
        _o.name = "tv_screen" if _part == "room" else "laptop_screen"
    else:
        _o.name = f"{_part}__{_o.name}"

# -------------------------------------------------------------- bake the room's light into each object's picture
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SPEC.get("bake_samples", 48)
sc.render.bake.margin = 6
sc.render.bake.target = "IMAGE_TEXTURES"
for _c in sc.view_layers[0].layer_collection.children:
    _c.exclude = False
    _c.holdout = False


def _area(o):
    return sum(p.area for p in o.data.polygons)


_baked = []
for _i, _o in enumerate(_meshes):
    if _o.name in ("tv_screen", "laptop_screen") or not _o.data.polygons:
        continue
    _a = _area(_o)
    _size = int(max(32, min(1024, 2 ** round(_math.log2(max(32, 380 * _math.sqrt(_a) * _TEX))))))
    bpy.ops.object.select_all(action="DESELECT"); _o.select_set(True); bpy.context.view_layer.objects.active = _o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=_math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    _img = bpy.data.images.new(f"bake_{_i}", _size, _size, float_buffer=True)
    for _m in _o.data.materials:
        if not _m:
            continue
        _n = _m.node_tree.nodes.new("ShaderNodeTexImage"); _n.image = _img
        _m.node_tree.nodes.active = _n
    try:
        # no glossy: a baked reflection is only right from one place (it made bright patches on the floor)
        # reflections are baked (metal, gloss, slat sheen) except on the floor, where a baked reflection is only right
        # from one place and showed as bright patches from other shots
        _floor = _a > 20 and max(v.co.z for v in _o.data.vertices) < 0.2
        _passes = {"DIRECT", "INDIRECT", "DIFFUSE", "EMIT", "TRANSMISSION"} | (set() if _floor else {"GLOSSY"})
        bpy.ops.object.bake(type="COMBINED", pass_filter=_passes)
    except RuntimeError as _err:
        print("bake skipped", _o.name, _err)
        continue
    # through the studio's own view transform (AgX, Medium High Contrast): the picture IS what the camera saw
    _png = _os.path.join(_DIR, f"{_i:04d}.png")
    _img.save_render(_png, scene=sc)
    _tex = bpy.data.images.load(_png)
    _bm = bpy.data.materials.new(f"baked_{_i}"); _bm.use_nodes = True
    _bs = _bm.node_tree.nodes["Principled BSDF"]
    _t = _bm.node_tree.nodes.new("ShaderNodeTexImage"); _t.image = _tex
    _bm.node_tree.links.new(_t.outputs["Color"], _bs.inputs["Base Color"])
    _bm["baked"] = 1
    _o.data.materials.clear(); _o.data.materials.append(_bm)
    _baked.append(_o.name)
    if _i % 20 == 0:
        print("baked", _i, "of", len(_meshes), flush=True)

# lights and the camera stay out of the file; the player draws baked pictures as they are
for _o in list(sc.objects):
    if _o.type != "MESH":
        bpy.data.objects.remove(_o, do_unlink=True)


def _pivot(part):
    pts = [v.co for o in sc.objects if o.type == "MESH" and (o.name.startswith(part + "__") or
           (part == "laptop" and o.name == "laptop_screen")) for v in o.data.vertices]
    if not pts:
        return None
    lo = _V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = _V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return {"min": list(lo), "max": list(hi), "base": [(lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z]}


bpy.ops.export_scene.gltf(filepath=_OUT, export_format="GLB", export_apply=False, export_yup=True,
                          export_extras=True, export_image_format="JPEG", export_jpeg_quality=90)
_info = {
    "fmt": FMT, "w": W, "h": H,
    "camera": {"pos": list(CAM), "lens": LENS, "sensor": SENSOR, "shift_y": SHIFT_Y, "tilt": TILT},
    "pieces": {p: _pivot(p) for p in ("chair", "laptop", "mug", "mic")},
    "screens": {"tv": "tv_screen", "laptop": "laptop_screen"},
    "screen_px": screen_px,
    "desk": {"top_z": top_z, "front_y": CAM.y + DD, "x": [cxT - half, cxT + half]},
    "seat": {"chair_y": CAM.y + DC, "x": float(cbase.x), "z": float(cbase.z)},
    "baked": len(_baked),
}
with open(_os.path.splitext(_OUT)[0] + "-set.json", "w") as _fh:
    _json.dump(_info, _fh, indent=1, default=float)
print("studio exported", _OUT, len(_baked), "baked")
