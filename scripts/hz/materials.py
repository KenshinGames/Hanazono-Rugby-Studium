"""マテリアル。名前で取り出す。色はリニア RGB。"""
import bpy

_defs = {}
_cache = {}


def srgb(r, g, b):
    """sRGB(0-255) をリニアに直す。"""
    def f(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), 1.0)


def _principled(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0,
                alpha=1.0, transmission=0.0, spec=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit is not None:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    m.diffuse_color = color
    return m


def define(name, **kw):
    _defs[name] = kw


def get(name):
    if name in _cache:
        return _cache[name]
    if name in _builders:
        m = _builders[name]()
    else:
        m = _principled(name, **_defs[name])
    _cache[name] = m
    return m


def clear():
    _cache.clear()


# ---- 手続きで作るもの ----

def _grass():
    m = bpy.data.materials.new("grass")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Position"], sep.inputs[0])

    def stripe(axis_out, width, offset):
        a = N.new("ShaderNodeMath"); a.operation = "ADD"
        a.inputs[1].default_value = 1000.0 + offset
        L.new(axis_out, a.inputs[0])
        d = N.new("ShaderNodeMath"); d.operation = "DIVIDE"
        d.inputs[1].default_value = width
        L.new(a.outputs[0], d.inputs[0])
        fl = N.new("ShaderNodeMath"); fl.operation = "FLOOR"
        L.new(d.outputs[0], fl.inputs[0])
        mo = N.new("ShaderNodeMath"); mo.operation = "MODULO"
        mo.inputs[1].default_value = 2.0
        L.new(fl.outputs[0], mo.inputs[0])
        return mo.outputs[0]

    from . import config
    t = config.load()["turf"]
    # ゴールラインに平行な帯(幅 5 m)。22 m ラインなどと境目が合うよう 0 を境にする
    s_cross = stripe(sep.outputs["X"], t["stripe_width_cross"], 0.0)
    s_long = stripe(sep.outputs["Y"], t["stripe_width_long"], 0.0)
    mix = N.new("ShaderNodeMath"); mix.operation = "MULTIPLY_ADD"
    mix.inputs[1].default_value = 0.85
    L.new(s_cross, mix.inputs[0])
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
    m2.inputs[1].default_value = 0.15
    L.new(s_long, m2.inputs[0])
    L.new(m2.outputs[0], mix.inputs[2])

    # むら
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.12
    noise.inputs["Detail"].default_value = 6.0
    L.new(geo.outputs["Position"], noise.inputs["Vector"])
    fine = N.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 18.0
    fine.inputs["Detail"].default_value = 3.0
    L.new(geo.outputs["Position"], fine.inputs["Vector"])

    ramp = N.new("ShaderNodeMix"); ramp.data_type = "RGBA"
    ramp.inputs["A"].default_value = (0.017, 0.072, 0.008, 1)
    ramp.inputs["B"].default_value = (0.028, 0.105, 0.012, 1)
    L.new(mix.outputs[0], ramp.inputs["Factor"])
    var = N.new("ShaderNodeMix"); var.data_type = "RGBA"; var.blend_type = "MULTIPLY"
    var.inputs["Factor"].default_value = 0.35
    L.new(ramp.outputs["Result"], var.inputs["A"])
    L.new(noise.outputs["Color"], var.inputs["B"])
    cr = N.new("ShaderNodeMix"); cr.data_type = "RGBA"; cr.blend_type = "OVERLAY"
    cr.inputs["Factor"].default_value = 0.25
    L.new(var.outputs["Result"], cr.inputs["A"])
    L.new(fine.outputs["Color"], cr.inputs["B"])
    L.new(cr.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    b.inputs["Specular IOR Level"].default_value = 0.25
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.03
    L.new(fine.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def _noisy(name, color, rough, scale=1.5, amount=0.25, bump=0.0, metal=0.0):
    """色にゆるいむらを入れたマテリアル(コンクリートや舗装)。"""
    def build():
        m = _principled(name, color, rough=rough, metal=metal)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")
        noise = N.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = 8.0
        noise.inputs["Roughness"].default_value = 0.65
        L.new(geo.outputs["Position"], noise.inputs["Vector"])
        mp = N.new("ShaderNodeMapRange")
        mp.inputs["To Min"].default_value = 1.0 - amount
        mp.inputs["To Max"].default_value = 1.0 + amount
        L.new(noise.outputs["Fac"], mp.inputs["Value"])
        mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        mul.inputs["A"].default_value = color
        L.new(mp.outputs["Result"], mul.inputs["B"])
        L.new(mul.outputs["Result"], b.inputs["Base Color"])
        if bump:
            bp = N.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            bp.inputs["Distance"].default_value = 0.01
            n2 = N.new("ShaderNodeTexNoise")
            n2.inputs["Scale"].default_value = 60.0
            L.new(geo.outputs["Position"], n2.inputs["Vector"])
            L.new(n2.outputs["Fac"], bp.inputs["Height"])
            L.new(bp.outputs["Normal"], b.inputs["Normal"])
        return m
    return build


_builders = {
    "grass": _grass,
    "concrete": _noisy("concrete", srgb(176, 174, 168), 0.85, scale=0.8, amount=0.10, bump=0.15),
    "concrete_dark": _noisy("concrete_dark", srgb(120, 120, 118), 0.9, scale=0.8, amount=0.12, bump=0.15),
    "concrete_light": _noisy("concrete_light", srgb(205, 203, 197), 0.8, scale=0.8, amount=0.07, bump=0.1),
    "asphalt": _noisy("asphalt", srgb(92, 92, 94), 0.95, scale=0.5, amount=0.15, bump=0.2),
    "paving_brick": _noisy("paving_brick", srgb(176, 132, 112), 0.9, scale=0.6, amount=0.12, bump=0.15),
    "paving_grey": _noisy("paving_grey", srgb(170, 168, 162), 0.9, scale=0.6, amount=0.10, bump=0.15),
    "apron": _noisy("apron", srgb(24, 112, 48), 0.9, scale=2.0, amount=0.10, bump=0.3),
    "lawn": _noisy("lawn", srgb(74, 110, 52), 0.95, scale=0.3, amount=0.25, bump=0.3),
    "dirt": _noisy("dirt", srgb(170, 150, 118), 0.95, scale=0.3, amount=0.15),
}

# ---- 単色のもの ----
define("line_white", color=srgb(238, 240, 236), rough=0.8)
define("white_paint", color=srgb(236, 236, 232), rough=0.45)
define("white_steel", color=srgb(228, 230, 230), rough=0.4, metal=0.0)
define("grey_steel", color=srgb(140, 144, 148), rough=0.45, metal=0.6)
define("dark_steel", color=srgb(38, 40, 44), rough=0.5, metal=0.3)
define("black", color=srgb(16, 16, 18), rough=0.6)
define("pad_white", color=srgb(240, 240, 240), rough=0.55)
define("pad_red", color=srgb(196, 30, 36), rough=0.55)
define("flag_red", color=srgb(214, 36, 40), rough=0.7)
define("seat_red", color=srgb(214, 44, 38), rough=0.42)
define("seat_blue", color=srgb(34, 70, 170), rough=0.42)
define("seat_grey", color=srgb(150, 152, 156), rough=0.42)
define("glass", color=srgb(150, 175, 185), rough=0.06, metal=0.0, transmission=0.0, alpha=1.0, spec=1.0, coat=1.0)
define("glass_dark", color=srgb(34, 44, 52), rough=0.05, spec=1.0, coat=1.0)
define("poly_clear", color=srgb(225, 235, 240), rough=0.15, alpha=0.35)
define("bench_blue", color=srgb(30, 60, 130), rough=0.5)
define("aluminium", color=srgb(190, 192, 194), rough=0.35, metal=0.9)
define("roof_sheet", color=srgb(196, 198, 196), rough=0.55, metal=0.2)
define("roof_under", color=srgb(214, 214, 210), rough=0.6)
define("screen_frame", color=srgb(52, 56, 60), rough=0.5)
define("lamp_off", color=srgb(210, 212, 205), rough=0.3)
