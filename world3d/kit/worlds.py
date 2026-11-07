"""Reusable worlds. A world is a complete place: it stays fixed and objects move inside it."""
import math

import bpy
from mathutils import Vector

from . import assets
from .registry import worlds

EARTH_RADIUS = 600.0


def _stars(world, density, brightness):
    """Stars generated in the sky shader, so they stay sharp at any camera angle."""
    t = world.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputWorld")
    bg = t.nodes.new("ShaderNodeBackground")
    coord = t.nodes.new("ShaderNodeTexCoord")
    vor = t.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = density
    vor.inputs["Randomness"].default_value = 1.0
    t.links.new(coord.outputs["Generated"], vor.inputs["Vector"])
    ramp = t.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.07
    ramp.inputs["From Max"].default_value = 0.0
    ramp.inputs["To Max"].default_value = 1.0
    t.links.new(vor.outputs["Distance"], ramp.inputs["Value"])
    sel = t.nodes.new("ShaderNodeMath")
    sel.operation = "GREATER_THAN"
    sel.inputs[1].default_value = 0.84
    t.links.new(vor.outputs["Color"], sel.inputs[0])
    mul = t.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    t.links.new(ramp.outputs[0], mul.inputs[0])
    t.links.new(sel.outputs[0], mul.inputs[1])
    gain = t.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = brightness
    t.links.new(mul.outputs[0], gain.inputs[0])
    bg.inputs["Color"].default_value = (0.75, 0.82, 1.0, 1)
    t.links.new(gain.outputs[0], bg.inputs["Strength"])
    t.links.new(bg.outputs[0], out.inputs["Surface"])


def _image(tree, name, linear=False):
    n = tree.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(assets.fetch(name), check_existing=True)
    n.interpolation = "Cubic"
    if linear:
        n.image.colorspace_settings.name = "Non-Color"
    return n


def _sphere(name, radius, material, center):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=radius, location=center)
    ob = bpy.context.object
    ob.name = name
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(material)
    return ob


def _earth_material():
    m = bpy.data.materials.new("earth")
    m.use_nodes = True
    t = m.node_tree
    b = t.nodes["Principled BSDF"]
    uv = t.nodes.new("ShaderNodeTexCoord")
    day, water, bump = _image(t, "earth_day"), _image(t, "earth_water", True), _image(t, "earth_bump", True)
    for n in (day, water, bump):
        t.links.new(uv.outputs["UV"], n.inputs["Vector"])
    richer = t.nodes.new("ShaderNodeHueSaturation")
    richer.inputs["Saturation"].default_value = 1.35
    richer.inputs["Value"].default_value = 0.9
    t.links.new(day.outputs["Color"], richer.inputs["Color"])
    t.links.new(richer.outputs["Color"], b.inputs["Base Color"])
    rough = t.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.75
    rough.inputs["To Max"].default_value = 0.28
    t.links.new(water.outputs["Color"], rough.inputs["Value"])
    t.links.new(rough.outputs[0], b.inputs["Roughness"])
    bn = t.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.35
    bn.inputs["Distance"].default_value = 2.0
    t.links.new(bump.outputs["Color"], bn.inputs["Height"])
    t.links.new(bn.outputs[0], b.inputs["Normal"])
    return m


def _clouds_material():
    m = bpy.data.materials.new("clouds")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    uv = t.nodes.new("ShaderNodeTexCoord")
    tex = _image(t, "earth_clouds", True)
    t.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    shape = t.nodes.new("ShaderNodeMapRange")
    shape.inputs["From Min"].default_value = 0.05
    shape.inputs["From Max"].default_value = 0.85
    t.links.new(tex.outputs["Alpha"], shape.inputs["Value"])
    white = t.nodes.new("ShaderNodeBsdfDiffuse")
    white.inputs["Color"].default_value = (0.95, 0.95, 0.96, 1)
    clear = t.nodes.new("ShaderNodeBsdfTransparent")
    mix = t.nodes.new("ShaderNodeMixShader")
    t.links.new(shape.outputs[0], mix.inputs[0])
    t.links.new(clear.outputs[0], mix.inputs[1])
    t.links.new(white.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def _atmosphere_material(sun_dir):
    """A thin blue rim that fades into space and only glows on the sunlit side."""
    m = bpy.data.materials.new("atmosphere")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    add = t.nodes.new("ShaderNodeAddShader")
    clear = t.nodes.new("ShaderNodeBsdfTransparent")
    em = t.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.13, 0.36, 1.0, 1)
    geo = t.nodes.new("ShaderNodeNewGeometry")
    rim = t.nodes.new("ShaderNodeLayerWeight")
    rim.inputs["Blend"].default_value = 0.42
    powr = t.nodes.new("ShaderNodeMath")
    powr.operation = "POWER"
    powr.inputs[1].default_value = 3.0
    t.links.new(rim.outputs["Facing"], powr.inputs[0])
    dot = t.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = tuple(sun_dir)
    t.links.new(geo.outputs["Normal"], dot.inputs[0])
    lit = t.nodes.new("ShaderNodeMapRange")
    lit.inputs["From Min"].default_value = -0.15
    lit.inputs["From Max"].default_value = 0.35
    t.links.new(dot.outputs["Value"], lit.inputs["Value"])
    mul = t.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    t.links.new(powr.outputs[0], mul.inputs[0])
    t.links.new(lit.outputs[0], mul.inputs[1])
    gain = t.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = 1.6
    t.links.new(mul.outputs[0], gain.inputs[0])
    t.links.new(gain.outputs[0], em.inputs["Strength"])
    t.links.new(clear.outputs[0], add.inputs[0])
    t.links.new(em.outputs[0], add.inputs[1])
    t.links.new(add.outputs[0], out.inputs["Surface"])
    return m


@worlds.add("space")
def space(scene, cfg):
    altitude = cfg.get("altitude", 150.0)
    center = (0, 0, -(EARTH_RADIUS + altitude))
    sun_dir = Vector(cfg.get("sun_dir", (0.55, -0.55, 0.62))).normalized()
    _stars(scene.world, cfg.get("star_density", 170), cfg.get("star_brightness", 14.0))
    earth = _sphere("earth", EARTH_RADIUS, _earth_material(), center)
    clouds = _sphere("clouds", EARTH_RADIUS * 1.003, _clouds_material(), center)
    air = _sphere("atmosphere", EARTH_RADIUS * 1.022, _atmosphere_material(sun_dir), center)
    air.visible_shadow = False
    clouds.visible_shadow = False
    turn = (math.radians(cfg.get("lon", 40)), math.radians(cfg.get("lat", -25)), 0)
    for ob in (earth, clouds):
        ob.rotation_euler = (turn[1], 0, turn[0])
    return {"sun_dir": sun_dir, "earth": earth, "clouds": clouds}


@worlds.add("studio")
def studio(scene, cfg):
    """Dark endless stage. The grid fades into the dark long before any edge, and the floor stands
    exactly under the object (see stand_on)."""
    bg = (0.010, 0.012, 0.017)
    t = scene.world.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputWorld")
    back = t.nodes.new("ShaderNodeBackground")
    back.inputs["Color"].default_value = (*bg, 1)
    t.links.new(back.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "floor"
    m = bpy.data.materials.new("grid_floor")
    m.use_nodes = True
    n = m.node_tree
    b = n.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.62
    b.inputs["Specular IOR Level"].default_value = 0.08
    tc = n.nodes.new("ShaderNodeTexCoord")
    grid = n.nodes.new("ShaderNodeTexBrick")
    grid.offset, grid.squash = 0.0, 1.0
    grid.inputs["Color1"].default_value = (*bg, 1)
    grid.inputs["Color2"].default_value = (*bg, 1)
    grid.inputs["Mortar"].default_value = (0.07, 0.095, 0.15, 1)
    grid.inputs["Scale"].default_value = 1.0
    grid.inputs["Mortar Size"].default_value = 0.025
    grid.inputs["Brick Width"].default_value = 2.5
    grid.inputs["Row Height"].default_value = 2.5
    n.links.new(tc.outputs["Object"], grid.inputs["Vector"])
    dist = n.nodes.new("ShaderNodeVectorMath")
    dist.operation = "LENGTH"
    n.links.new(tc.outputs["Object"], dist.inputs[0])
    fade = n.nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = cfg.get("fade_from", 14)
    fade.inputs["From Max"].default_value = cfg.get("fade_to", 60)
    fade.inputs["To Min"].default_value = 1.0
    fade.inputs["To Max"].default_value = 0.0
    n.links.new(dist.outputs["Value"], fade.inputs["Value"])
    mix = n.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*bg, 1)
    n.links.new(fade.outputs[0], mix.inputs["Factor"])
    n.links.new(grid.outputs["Color"], mix.inputs["B"])
    n.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    spec = n.nodes.new("ShaderNodeMath")
    spec.operation = "MULTIPLY"
    spec.inputs[1].default_value = 0.08
    n.links.new(fade.outputs[0], spec.inputs[0])
    n.links.new(spec.outputs[0], b.inputs["Specular IOR Level"])
    floor.data.materials.append(m)
    return {"floor": floor}


def stand_on(world, model):
    """Put a world's floor under the object's lowest point."""
    floor = world.get("floor")
    if floor is not None:
        # On the ground nothing opens downward, so wheels and bases stay on the floor.
        for p in model.parts.values():
            p.explode.z = abs(p.explode.z)
        floor.location.z = model.lowest() - 0.01
