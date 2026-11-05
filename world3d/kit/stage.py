"""Scene reset and render settings."""
import bpy

QUALITY = {
    "smoke": {"size": (480, 270), "samples": 4},
    "draft": {"size": (960, 540), "samples": 8},
    "video": {"size": (1280, 720), "samples": 12},
    "final": {"size": (1920, 1080), "samples": 64},
}


def reset(quality, fps, vertical=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    q = QUALITY[quality]
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = reversed(q["size"]) if vertical else q["size"]
    r.resolution_percentage = 100
    r.fps = fps
    r.image_settings.file_format = "PNG"
    r.film_transparent = False
    c = scene.cycles
    c.device = "CPU"
    c.samples = q["samples"]
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.03
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.max_bounces = 4
    c.diffuse_bounces = 2
    c.glossy_bounces = 3
    c.transmission_bounces = 2
    c.transparent_max_bounces = 6
    c.caustics_reflective = c.caustics_refractive = False
    r.use_persistent_data = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    scene.world = world
    return scene
