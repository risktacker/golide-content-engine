"""Compiles a blueprint (JSON facts about a real object) into a 3D object made of parts."""
import json
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
    def __init__(self, blueprint, root, built):
        self.blueprint, self.root, self.parts = blueprint, root, {p.id: p for p in built}

    def meshes(self):
        return [m for p in self.parts.values() for m in p.meshes]

    def part(self, pid):
        if pid not in self.parts:
            raise KeyError(f"Unknown part '{pid}'. Available: {sorted(self.parts)}")
        return self.parts[pid]


def load_blueprint(name):
    path = ROOT / "blueprints" / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No blueprint: {path}")
    return json.loads(path.read_text())


def build(name):
    bp = load_blueprint(name)
    scene = bpy.context.scene
    root = bpy.data.objects.new(name, None)
    scene.collection.objects.link(root)
    built = []
    for spec in bp["parts"]:
        group = bpy.data.objects.new(spec["id"], None)
        scene.collection.objects.link(group)
        group.parent = root
        group.location = Vector(spec.get("at", (0, 0, 0)))
        material = mats.get(spec["material"])
        meshes = parts.get(spec["builder"])(spec.get("params", {}), material)
        for mesh in meshes:
            mesh.parent = group
        built.append(Part(spec, group, meshes))
    return Model(bp, root, built)
