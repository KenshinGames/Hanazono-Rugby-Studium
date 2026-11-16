"""昼と夜の光。描く直前に呼ぶ(1 つの .blend で両方に切り替えられる)。"""
import math

import bpy
from mathutils import Vector

from . import config

# 昼の太陽: 午後の南西の日(バックスタンドと映像装置に日が当たり、メインスタンドの中は屋根の影)
DAY_SUN_AZIMUTH = 228.0
DAY_SUN_ELEVATION = 47.0


def sun_vector(az_deg, el_deg):
    """方位角(北=0、東=90)と高度から、太陽へ向かう単位ベクトル(シーンの座標)。"""
    ax = math.radians(config.load()["site"]["x_axis_azimuth_deg"])
    # +X の方位が ax。方位 az の水平の向きは +X から時計回りに (az-ax)。時計回り = -Y の側へ
    d = math.radians(az_deg) - ax
    el = math.radians(el_deg)
    return Vector((math.cos(d) * math.cos(el), -math.sin(d) * math.cos(el), math.sin(el)))


def _world(scene):
    w = scene.world
    if w is None:
        w = bpy.data.worlds.new("world")
        scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    return w, nt


def _set_night_collections(night):
    for c in bpy.data.collections:
        if c.name.startswith("night_"):
            c.hide_render = not night
        if c.name.startswith("day_"):
            c.hide_render = night
    # 光る面(投光器のレンズ、映像装置)は夜だけ強くする
    for m in bpy.data.materials:
        if "emit_day" in m and m.use_nodes:
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Emission Strength"].default_value = m["emit_night"] if night else m["emit_day"]


def setup_day(scene, az=DAY_SUN_AZIMUTH, el=DAY_SUN_ELEVATION):
    w, nt = _world(scene)
    v = sun_vector(az, el)
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_elevation = math.radians(el)
    sky.sun_rotation = math.atan2(v.x, v.y)   # 調べた決まり: +Y から +X へ回る角
    sky.sun_intensity = 1.0
    sky.air_density = 1.0
    sky.aerosol_density = 1.6
    sky.ozone_density = 1.0
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.11
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    _set_night_collections(False)
    scene.view_settings.exposure = 0.45


def setup_night(scene):
    w, nt = _world(scene)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.010, 0.014, 0.030, 1)
    bg.inputs["Strength"].default_value = 0.35
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    _set_night_collections(True)
    scene.view_settings.exposure = 0.0


def setup_render(scene, samples=64, res=(1600, 900)):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception as e:  # GPU が使えなければ CPU で続ける
        print("GPU を使えません:", e)
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.sample_clamp_indirect = 8.0
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    import os
    scene.view_settings.view_transform = os.environ.get("HZ_VT", "AgX")
    try:
        scene.view_settings.look = os.environ.get("HZ_LOOK", "AgX - Punchy")
    except Exception as e:
        print("[render] look を設定できません", e)
    print("[render] view", scene.view_settings.view_transform, scene.view_settings.look)
    scene.render.image_settings.file_format = "PNG"
