"""Camera moves. Each returns an update(t) function; the shot only names the move."""
import math

import bpy
from mathutils import Quaternion, Vector

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
    cam.rotation_quaternion = q @ Quaternion((0, 0, 1), math.radians(roll_deg))


def fit_distance(cam, radius, margin=1.12):
    """Distance at which a sphere of this radius fills the narrow side of the frame."""
    r = bpy.context.scene.render
    long_side, short_side = max(r.resolution_x, r.resolution_y), min(r.resolution_x, r.resolution_y)
    half = math.atan(math.tan(cam.data.angle / 2) * short_side / long_side)
    return margin * radius / math.sin(half)


@cameras.add("orbit")
def orbit(cam, cfg, duration, model):
    tgt = Vector(cfg.get("target", (0, 0, 0)))
    a0, a1 = math.radians(cfg.get("yaw_from", 0)), math.radians(cfg.get("yaw_to", 40))
    p0, p1 = math.radians(cfg.get("pitch_from", 30)), math.radians(cfg.get("pitch_to", 30))
    d0 = fit_distance(cam, model.radius) * cfg.get("zoom_from", 1.0)
    d1 = fit_distance(cam, model.radius) * cfg.get("zoom_to", 1.0)
    if cfg.get("fit_exploded"):
        d1 = max(d1, fit_distance(cam, model.exploded_radius))
    aim = Vector(cfg.get("aim_offset", (0, 0, 0)))
    roll = cfg.get("roll", 0)

    def update(t):
        u = smooth(t / duration) * 0.6 + (t / duration) * 0.4
        yaw, pitch, dist = a0 + (a1 - a0) * u, p0 + (p1 - p0) * u, d0 + (d1 - d0) * u
        pos = tgt + dist * Vector((math.cos(pitch) * math.sin(yaw), -math.cos(pitch) * math.cos(yaw), math.sin(pitch)))
        _look(cam, pos, tgt + aim, roll)

    return update
