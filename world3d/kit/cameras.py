"""Camera moves. Each returns an update(t) function; the shot only names the move."""
import math

import bpy
from mathutils import Vector

from .ease import smooth
from .registry import cameras


def make(cfg):
    d = bpy.data.cameras.new("cam")
    d.lens = cfg.get("lens", 40)
    d.sensor_width = 36
    d.clip_start, d.clip_end = 0.1, 6000
    ob = bpy.data.objects.new("cam", d)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    ob.rotation_mode = "QUATERNION"
    return ob


def _look(cam, position, target, roll_deg=0):
    cam.location = position
    q = (Vector(target) - position).to_track_quat("-Z", "Y")
    from mathutils import Quaternion
    cam.rotation_quaternion = q @ Quaternion((0, 0, 1), math.radians(roll_deg))


@cameras.add("orbit")
def orbit(cam, cfg, duration):
    tgt = Vector(cfg.get("target", (0, 0, 0)))
    a0, a1 = math.radians(cfg.get("yaw_from", 0)), math.radians(cfg.get("yaw_to", 40))
    p0, p1 = math.radians(cfg.get("pitch_from", 30)), math.radians(cfg.get("pitch_to", 30))
    d0, d1 = cfg.get("dist_from", 30), cfg.get("dist_to", 30)
    aim = Vector(cfg.get("aim_offset", (0, 0, 0)))
    roll = cfg.get("roll", 0)

    def update(t):
        u = smooth(t / duration) * 0.6 + (t / duration) * 0.4
        yaw, pitch, dist = a0 + (a1 - a0) * u, p0 + (p1 - p0) * u, d0 + (d1 - d0) * u
        pos = tgt + dist * Vector((math.cos(pitch) * math.sin(yaw), -math.cos(pitch) * math.cos(yaw), math.sin(pitch)))
        _look(cam, pos, tgt + aim, roll)

    return update
