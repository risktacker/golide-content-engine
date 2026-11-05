"""Effects. Each returns update(t). Heavy simulation never runs per video."""
import math

import bpy
import bmesh
from mathutils import Matrix, Vector

from . import materials as mats
from .ease import smooth, span
from .registry import effects


@effects.add("signal_beam")
def signal_beam(model, cfg):
    """Pulses of light travelling from a part's anchor out along a direction."""
    part = model.part(cfg["from"])
    direction = Vector(cfg.get("direction", (-0.8, 0.2, 0.56))).normalized()
    length, count = cfg.get("length", 60), cfg.get("pulses", 7)
    speed, a, b = cfg.get("speed", 14), cfg["start"], cfg["end"]
    width = cfg.get("width", 0.14)
    rings = []
    align = direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    for i in range(count):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=1.0, radius2=1.0, depth=width)
        me = bpy.data.meshes.new(f"pulse{i}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"pulse{i}", me)
        bpy.context.scene.collection.objects.link(ob)
        m = mats.get("beam")
        me.materials.append(m)
        ob.visible_shadow = False
        rings.append((ob, m.node_tree.nodes["beam_emission"]))
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.035, radius2=0.035, depth=1.0)
    me = bpy.data.meshes.new("beam_core")
    bm.to_mesh(me)
    bm.free()
    core = bpy.data.objects.new("beam_core", me)
    bpy.context.scene.collection.objects.link(core)
    core_mat = mats.get("beam")
    me.materials.append(core_mat)
    core.visible_shadow = False
    core_em = core_mat.node_tree.nodes["beam_emission"]

    def update(t):
        bpy.context.view_layer.update()
        o = part.anchor_world()
        vis = smooth(span(t, a, a + 0.6)) * (1 - smooth(span(t, b - 0.5, b)))
        reach = length * smooth(span(t, a, a + 1.5))
        core.matrix_world = (Matrix.Translation(o + direction * reach / 2) @ align
                             @ Matrix.Diagonal((1, 1, max(reach, 0.01), 1)))
        core_em.inputs["Strength"].default_value = 7 * vis
        for i, (ob, em) in enumerate(rings):
            d = (speed * (t - a) + i * length / count) % length
            fade = (1 - d / length) * min(1.0, d / 2)
            r = 0.2 + d * math.tan(math.radians(cfg.get("spread_deg", 1.1)))
            ob.matrix_world = (Matrix.Translation(o + direction * d) @ align
                               @ Matrix.Diagonal((r, r, 1, 1)))
            em.inputs["Strength"].default_value = 10 * vis * fade if d < reach else 0

    return update
