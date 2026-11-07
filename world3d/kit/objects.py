"""Compiles a blueprint (JSON facts about a real object) into a 3D object made of parts."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

from . import materials as mats

ROOT = Path(__file__).resolve().parent.parent


class Part:
    def __init__(self, spec, group, meshes):
        self.id, self.label, self.spec = spec["id"], spec.get("label", spec["id"]), spec
        self.group, self.meshes = group, meshes
        self.home = group.location.copy()
        self.explode = Vector(spec.get("explode", (0, 0, 0)))
        self.anchor = Vector(spec.get("anchor", (0, 0, 0)))

    def anchor_world(self):
        return self.group.matrix_world @ self.anchor


class Model:
    def __init__(self, blueprint, root, content, built):
        self.blueprint, self.root, self.content = blueprint, root, content
        self.parts = {p.id: p for p in built}
        self.radius = 1.0

    def _corners(self, exploded):
        bpy.context.view_layer.update()
        to_local = self.content.matrix_world.inverted()
        for p in self.parts.values():
            shift = p.explode if exploded else Vector((0, 0, 0))
            for mesh in p.meshes:
                for corner in mesh.bound_box:
                    yield to_local @ (mesh.matrix_world @ Vector(corner)) + shift

    def _extent(self, exploded):
        pts = list(self._corners(exploded))
        low = Vector((min(p[i] for p in pts) for i in range(3)))
        high = Vector((max(p[i] for p in pts) for i in range(3)))
        return (low + high) / 2, (high - low).length / 2

    def fit(self, size):
        """Any object, from a chip to a ship, is shown at one standard size, centred, so
        worlds and cameras never need to know how big the real thing is."""
        center, radius = self._extent(False)
        self.content.location = -center
        scale = size / radius
        self.root.scale = (scale, scale, scale)
        self.radius = radius * scale
        self.exploded_radius = self._extent(True)[1] * scale

    def lowest(self, exploded=False):
        """World height of the object's lowest point, so it can stand on the floor."""
        if exploded:
            for p in self.parts.values():
                p.group.location = p.home + p.explode
        bpy.context.view_layer.update()
        low = min((m.matrix_world @ Vector(c)).z for m in self.meshes() for c in m.bound_box)
        if exploded:
            for p in self.parts.values():
                p.group.location = p.home
            bpy.context.view_layer.update()
        return low

    def meshes(self):
        return [m for p in self.parts.values() for m in p.meshes]

    def part(self, pid):
        if pid not in self.parts:
            raise KeyError(f"Unknown part '{pid}'. Available: {sorted(self.parts)}")
        return self.parts[pid]


def load_blueprint(name, folder=None):
    folder = Path(folder or ROOT / "blueprints")
    path = folder / name / "blueprint.json"
    if not path.exists():
        path = folder / "blueprint.json"
    if not path.exists():
        raise FileNotFoundError(f"No blueprint: {path}")
    return json.loads(path.read_text())


def _import(path):
    """One CAD part as a smooth Blender mesh: sharp where the design has an edge, smooth elsewhere."""
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path))
    ob = next(o for o in bpy.data.objects if o not in before)
    for poly in ob.data.polygons:
        poly.use_smooth = True
    smooth = ob.modifiers.new("smooth_by_angle", "EDGE_SPLIT")
    smooth.split_angle = math.radians(32)
    return ob


def build(name, folder=None):
    """Every part comes from the object's CAD build (explain3d/cad.py), in place, with a label anchor
    on top of its own bounds, so any object works the same way."""
    folder = Path(folder or ROOT / "blueprints")
    bp = load_blueprint(name, folder)
    meshes_at = folder / name if (folder / name / "blueprint.json").exists() else folder
    scene = bpy.context.scene
    root = bpy.data.objects.new(name, None)
    content = bpy.data.objects.new(name + "_content", None)
    scene.collection.objects.link(root)
    scene.collection.objects.link(content)
    content.parent = root
    built = []
    for spec in bp["parts"]:
        group = bpy.data.objects.new(spec["id"], None)
        scene.collection.objects.link(group)
        group.parent = content
        mesh = _import(meshes_at / spec["mesh"])
        mesh.parent = group
        mesh.data.materials.clear()
        mesh.data.materials.append(mats.get(spec["material"]))
        lo, hi = Vector(spec["min"]), Vector(spec["max"])
        spec = {**spec, "anchor": [(lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z]}
        built.append(Part(spec, group, [mesh]))
    return Model(bp, root, content, built)
