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


def fit_distance(cam, radius, margin=0.92):
    """Distance at which a sphere of this radius fills the narrow side of the frame."""
    r = bpy.context.scene.render
    long_side, short_side = max(r.resolution_x, r.resolution_y), min(r.resolution_x, r.resolution_y)
    half = math.atan(math.tan(cam.data.angle / 2) * short_side / long_side)
    return margin * radius / math.sin(half)


def _corners(model):
    """Every bounding-box corner of every part, where it is right now (moves and explodes included)."""
    bpy.context.view_layer.update()
    return [m.matrix_world @ Vector(c) for m in model.meshes() for c in m.bound_box]


def _tangents(cam):
    r = bpy.context.scene.render
    wide = math.tan(cam.data.angle / 2)
    if r.resolution_x >= r.resolution_y:
        return wide, wide * r.resolution_y / r.resolution_x
    return wide * r.resolution_x / r.resolution_y, wide


def frame_all(cam, points, direction, target, fill=0.78):
    """Smallest distance along direction at which every point sits inside the frame, with room
    to spare for labels. Works for any shape: long, tall, flat or opened up."""
    tx, ty = _tangents(cam)
    forward = -direction.normalized()
    right = forward.cross(Vector((0, 0, 1)))
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(forward)
    need = 0.0
    for p in points:
        v = p - target
        x, y, depth = v.dot(right), v.dot(up), v.dot(forward)
        # point fits when |x| <= fill*tx*(dist+depth) and the same for y
        need = max(need, abs(x) / (fill * tx) - depth, abs(y) / (fill * ty) - depth)
    return max(need, 0.5)


@cameras.add("orbit")
def orbit(cam, cfg, duration, model):
    """Turns round the object. Distance and aim are measured from the object every frame, so it is
    always whole and centred, then the move's zoom adds a push in or pull out."""
    a0, a1 = math.radians(cfg.get("yaw_from", 0)), math.radians(cfg.get("yaw_to", 40))
    p0, p1 = math.radians(cfg.get("pitch_from", 30)), math.radians(cfg.get("pitch_to", 30))
    z0, z1 = cfg.get("zoom_from", 1.0), cfg.get("zoom_to", 1.0)
    aim = Vector(cfg.get("aim_offset", (0, 0, 0)))
    roll = cfg.get("roll", 0)

    def update(t):
        u = smooth(t / duration) * 0.6 + (t / duration) * 0.4
        yaw, pitch = a0 + (a1 - a0) * u, p0 + (p1 - p0) * u
        direction = Vector((math.cos(pitch) * math.sin(yaw), -math.cos(pitch) * math.cos(yaw), math.sin(pitch)))
        pts = _corners(model)
        low = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        high = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        target = (low + high) / 2
        dist = frame_all(cam, pts, direction, target) * (z0 + (z1 - z0) * u)
        _look(cam, target + dist * direction, target + aim, roll)

    return update
