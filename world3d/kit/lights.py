"""Light rigs. A world picks a rig; objects never carry their own lights."""
import math

import bpy
from mathutils import Vector

from .registry import lights


def _receivers(name, objects):
    """Collection used to light some objects only."""
    c = bpy.data.collections.new(name)
    for ob in objects:
        c.objects.link(ob)
    return c


def _sun(name, direction, strength, color, angle_deg, shadow=True, receivers=None):
    d = bpy.data.lights.new(name, "SUN")
    d.energy, d.color, d.angle = strength, color, math.radians(angle_deg)
    d.use_shadow = shadow
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector(direction).to_track_quat("Z", "Y")
    if receivers:
        ob.light_linking.receiver_collection = _receivers(name + "_targets", receivers)
    return ob


@lights.add("sun_space")
def sun_space(world, cfg, objects):
    """Hard sunlight, plus a weak blue bounce from the Earth so shadow sides keep shape."""
    color = (1.0, 0.97, 0.92)
    planet = [world["earth"], world["clouds"]]
    _sun("sun_planet", world["sun_dir"], cfg.get("sun_planet", 1.5), color, 0.6, shadow=False, receivers=planet)
    _sun("sun", world["sun_dir"], cfg.get("sun", 5.5), color, 0.6, receivers=objects)
    _sun("earthshine", (0, 0, -1), cfg.get("earthshine", 0.7), (0.5, 0.68, 1.0), 40, receivers=objects)


@lights.add("studio_soft")
def studio_soft(world, cfg, objects):
    """Key from the front side, cool rim behind, so any shape reads on a dark stage."""
    _sun("key", (0.5, -0.65, 0.6), cfg.get("key", 3.0), (1.0, 0.97, 0.93), 8)
    _sun("rim", (-0.6, 0.7, 0.35), cfg.get("rim", 2.2), (0.6, 0.76, 1.0), 4, receivers=objects)
    _sun("fill", (-0.2, -0.6, -0.5), cfg.get("fill", 0.5), (0.8, 0.88, 1.0), 45, receivers=objects)
