"""Compiles a blueprint (JSON facts about a real object) into a 3D object made of parts."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

from . import materials as mats
from .registry import parts

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
    path = Path(folder or ROOT / "blueprints") / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No blueprint: {path}")
    return json.loads(path.read_text())


def build(name, folder=None):
    bp = load_blueprint(name, folder)
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
        group.location = Vector(spec.get("at", (0, 0, 0)))
        group.rotation_euler = [math.radians(v) for v in spec.get("turn", (0, 0, 0))]
        material = mats.get(spec["material"])
        builder = parts.get(spec["builder"])
        params = spec.get("params", {})
        meshes = builder(params, material, spec["profile"]) if spec.get("profile") else builder(params, material)
        for mesh in meshes:
            mesh.parent = group
        built.append(Part(spec, group, meshes))
    return Model(bp, root, content, built)
