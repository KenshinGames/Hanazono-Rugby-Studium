"""昼と夜の光。描く直前に呼ぶ(1 つの .blend で両方に切り替えられる)。"""
import math
import os

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
    # ラベル "dn 昼 夜" の Value ノード(窓の明かり、虹色の帯、霞)を切り替える
    for m in bpy.data.materials:
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "VALUE" and n.label.startswith("dn "):
                    parts = n.label.split()
                    n.outputs[0].default_value = float(parts[2] if night else parts[1])
    # 光る面(投光器のレンズ、映像装置)は夜だけ強くする
    for m in bpy.data.materials:
        if "emit_day" in m and m.use_nodes:
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Emission Strength"].default_value = m["emit_night"] if night else m["emit_day"]


def setup_day(scene, az=DAY_SUN_AZIMUTH, el=DAY_SUN_ELEVATION, bg_strength=0.11, exposure=0.1, clouds=None):
    """clouds は夕方の雲の色 {"near": 太陽の側の色, "far": 反対側の色, "strength": 明るさ}。省くと白い雲。"""
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
    bg.inputs["Strength"].default_value = bg_strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(_clouds(nt, bg.outputs[0], clouds, v), out.inputs[0])
    _set_night_collections(False)
    scene.view_settings.exposure = exposure
    _glare(scene, False)


def setup_night(scene):
    w, nt = _world(scene)
    # 日が落ちたあとの濃い青。地平線は街の明かりで少し明るく暖かい
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.35
    L.new(sep.outputs["Z"], mr.inputs["Value"])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (0.060, 0.050, 0.060, 1)
    mx.inputs["B"].default_value = (0.016, 0.026, 0.062, 1)
    L.new(mr.outputs["Result"], mx.inputs["Factor"])
    bg = N.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.8
    L.new(mx.outputs["Result"], bg.inputs["Color"])
    out = N.new("ShaderNodeOutputWorld")
    L.new(bg.outputs[0], out.inputs[0])
    _set_night_collections(True)
    scene.view_settings.exposure = 0.0
    _glare(scene, True)


CLOUD_BRIGHT = float(os.environ.get("HZ_CLOUD", 1.6))
CLOUD_COVER = float(os.environ.get("HZ_COVER", 0.5))


def _clouds(nt, sky_shader, tint=None, sun=None):
    """空に雲を足す。視線の向きを高さ一定の面に映して雲の模様を作る。地平線の近くは薄く消す。
    tint を渡すと、太陽に近い雲ほど near の色、遠い雲ほど far の色にする(夕焼け)。"""
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])

    def mth(op, a, v=None, bs=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        L.new(a, n.inputs[0])
        if bs is not None:
            L.new(bs, n.inputs[1])
        elif v is not None:
            n.inputs[1].default_value = v
        return n.outputs[0]
    zc = mth("MAXIMUM", sep.outputs["Z"], 0.04)
    u = mth("DIVIDE", sep.outputs["X"], bs=zc)
    v = mth("DIVIDE", sep.outputs["Y"], bs=zc)
    cv = N.new("ShaderNodeCombineXYZ")
    L.new(u, cv.inputs[0]); L.new(v, cv.inputs[1])
    nz = N.new("ShaderNodeTexNoise"); nz.noise_dimensions = "3D"
    nz.inputs["Scale"].default_value = 0.9
    nz.inputs["Detail"].default_value = 8.0
    nz.inputs["Roughness"].default_value = 0.58
    L.new(cv.outputs[0], nz.inputs["Vector"])
    cover = N.new("ShaderNodeMapRange")
    cover.inputs["From Min"].default_value = 1.0 - CLOUD_COVER * 0.9
    cover.inputs["From Max"].default_value = 1.0 - CLOUD_COVER * 0.9 + 0.16
    L.new(nz.outputs["Fac"], cover.inputs["Value"])
    fade = N.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = 0.02
    fade.inputs["From Max"].default_value = 0.22
    L.new(sep.outputs["Z"], fade.inputs["Value"])
    mask = mth("MULTIPLY", cover.outputs["Result"], bs=fade.outputs["Result"])
    mask = mth("MULTIPLY", mask, 0.95)
    # 雲の明るさにむら(下が少し灰色)
    shade = N.new("ShaderNodeMapRange")
    shade.inputs["To Min"].default_value = 0.62
    shade.inputs["To Max"].default_value = 1.0
    L.new(nz.outputs["Fac"], shade.inputs["Value"])
    cb = N.new("ShaderNodeBackground")
    if tint:
        # 太陽の向きとの近さ(0〜1)を何乗かして、太陽のまわりだけ染める
        dp = N.new("ShaderNodeVectorMath"); dp.operation = "DOT_PRODUCT"
        L.new(tc.outputs["Generated"], dp.inputs[0])
        dp.inputs[1].default_value = tuple(sun)
        k = mth("MULTIPLY", mth("ADD", dp.outputs["Value"], 1.0), 0.5)
        k = mth("POWER", k, tint.get("power", 4.0))
        mc = N.new("ShaderNodeMix"); mc.data_type = "RGBA"
        L.new(k, mc.inputs["Factor"])
        mc.inputs["A"].default_value = tuple(tint["far"]) + (1.0,)
        mc.inputs["B"].default_value = tuple(tint["near"]) + (1.0,)
        mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        L.new(mc.outputs["Result"], mul.inputs["A"])
        L.new(shade.outputs["Result"], mul.inputs["B"])
        L.new(mul.outputs["Result"], cb.inputs["Color"])
        cb.inputs["Strength"].default_value = tint.get("strength", CLOUD_BRIGHT)
    else:
        col = N.new("ShaderNodeCombineColor")
        for i, k in enumerate((0.97, 0.98, 1.0)):
            mm = N.new("ShaderNodeMath"); mm.operation = "MULTIPLY"
            L.new(shade.outputs["Result"], mm.inputs[0]); mm.inputs[1].default_value = k
            L.new(mm.outputs[0], col.inputs[i])
        L.new(col.outputs[0], cb.inputs["Color"])
        cb.inputs["Strength"].default_value = CLOUD_BRIGHT
    ms = N.new("ShaderNodeMixShader")
    L.new(mask, ms.inputs[0])
    L.new(sky_shader, ms.inputs[1]); L.new(cb.outputs[0], ms.inputs[2])
    return ms.outputs[0]


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


def _glare(scene, on):
    """夜だけ、投光器のまわりに光のにじみを足す(コンポジター)。使えなければ何もしない。"""
    try:
        if not on:
            scene.compositing_node_group = None
            return
        nt = bpy.data.node_groups.get("hz_glare")
        if nt is None:
            nt = bpy.data.node_groups.new("hz_glare", "CompositorNodeTree")
            nt.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            rl = nt.nodes.new("CompositorNodeRLayers")
            gl = nt.nodes.new("CompositorNodeGlare")
            out = nt.nodes.new("NodeGroupOutput")
            for key, val in (("Type", "Fog Glow"), ("Quality", "High"), ("Threshold", float(os.environ.get("HZ_GT", 6.0))), ("Strength", float(os.environ.get("HZ_GS", 1.0))), ("Size", float(os.environ.get("HZ_GZ", 1.0)))):
                try:
                    gl.inputs[key].default_value = val
                except Exception as e:
                    print("[glare] 設定できない項目:", key, e)
            nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
            nt.links.new(gl.outputs["Image"], out.inputs[0])
        scene.compositing_node_group = nt
        scene.render.use_compositing = True
    except Exception as e:
        print("[glare] 光のにじみは使えません:", e)
