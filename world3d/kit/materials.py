"""Material library. Objects name a material; the look lives here once."""
import bpy

from .registry import materials


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    return m, m.node_tree, n["Principled BSDF"]


def _set(bsdf, color=None, metallic=None, roughness=None, emission=None, strength=None):
    i = bsdf.inputs
    if color: i["Base Color"].default_value = (*color, 1)
    if metallic is not None: i["Metallic"].default_value = metallic
    if roughness is not None: i["Roughness"].default_value = roughness
    if emission: i["Emission Color"].default_value = (*emission, 1)
    if strength is not None: i["Emission Strength"].default_value = strength


def _crinkle(t, bsdf, scale=6.0, strength=0.1, distance=0.04):
    """Wrinkled foil: soft noise on object coordinates, so sheets catch light unevenly."""
    tc = t.nodes.new("ShaderNodeTexCoord")
    noise = t.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 9
    noise.inputs["Roughness"].default_value = 0.62
    t.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    bump = t.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    t.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    t.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    ramp = t.nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value = 0.26
    ramp.inputs["To Max"].default_value = 0.5
    t.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
    t.links.new(ramp.outputs["Result"], bsdf.inputs["Roughness"])


@materials.add("foil_silver")
def foil_silver():
    m, t, b = _new("foil_silver")
    _set(b, (0.86, 0.87, 0.89), 1.0, 0.25)
    _crinkle(t, b)
    return m


@materials.add("foil_gold")
def foil_gold():
    m, t, b = _new("foil_gold")
    _set(b, (0.92, 0.62, 0.20), 1.0, 0.28)
    _crinkle(t, b, scale=9)
    return m


@materials.add("blanket_white")
def blanket_white():
    m, t, b = _new("blanket_white")
    _set(b, (0.80, 0.80, 0.77), 0.0, 0.5)
    _crinkle(t, b, scale=4, strength=0.06)
    return m


@materials.add("panel_grey")
def panel_grey():
    m, t, b = _new("panel_grey")
    _set(b, (0.42, 0.43, 0.45), 0.8, 0.42)
    return m


@materials.add("metal_dark")
def metal_dark():
    m, t, b = _new("metal_dark")
    _set(b, (0.05, 0.05, 0.06), 0.7, 0.45)
    return m


@materials.add("rail_yellow")
def rail_yellow():
    m, t, b = _new("rail_yellow")
    _set(b, (0.85, 0.60, 0.05), 0.0, 0.4)
    return m


@materials.add("mirror")
def mirror():
    m, t, b = _new("mirror")
    _set(b, (0.95, 0.96, 0.98), 1.0, 0.04)
    return m


@materials.add("black_inner")
def black_inner():
    m, t, b = _new("black_inner")
    _set(b, (0.01, 0.01, 0.012), 0.0, 0.7)
    return m


@materials.add("solar_cell")
def solar_cell():
    """Dark blue cells in a silver grid, generated so no texture is needed."""
    m, t, b = _new("solar_cell")
    _set(b, None, 0.5, 0.26)
    tc = t.nodes.new("ShaderNodeTexCoord")
    brick = t.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.squash = 1.0
    brick.inputs["Color1"].default_value = (0.004, 0.012, 0.075, 1)
    brick.inputs["Color2"].default_value = (0.006, 0.018, 0.10, 1)
    brick.inputs["Mortar"].default_value = (0.6, 0.62, 0.66, 1)
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Brick Width"].default_value = 0.20
    brick.inputs["Row Height"].default_value = 0.20
    t.links.new(tc.outputs["Object"], brick.inputs["Vector"])
    t.links.new(brick.outputs["Color"], b.inputs["Base Color"])
    return m


@materials.add("beam")
def beam():
    m = bpy.data.materials.new("beam")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    add = t.nodes.new("ShaderNodeAddShader")
    tr = t.nodes.new("ShaderNodeBsdfTransparent")
    em = t.nodes.new("ShaderNodeEmission")
    em.name = "beam_emission"
    em.inputs["Color"].default_value = (1.0, 0.62, 0.10, 1)
    em.inputs["Strength"].default_value = 0
    t.links.new(tr.outputs[0], add.inputs[0])
    t.links.new(em.outputs[0], add.inputs[1])
    t.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def get(name):
    """Each part gets its own copy so one part can glow without touching the others."""
    return materials.get(name)()


def set_glow(material, amount, color=(1.0, 0.62, 0.10)):
    b = material.node_tree.nodes.get("Principled BSDF")
    if b:
        _set(b, emission=color, strength=amount)
