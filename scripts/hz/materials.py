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


def emissive(name, color, day, night, base=None):
    """昼と夜で光の強さを切り替える面(sky.py が切り替える)。"""
    if name in _cache:
        return _cache[name]
    m = _principled(name, base or color, rough=0.3, emit=color, emit_strength=day)
    m["emit_day"] = float(day)
    m["emit_night"] = float(night)
    _cache[name] = m
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


def _scrum_tiles():
    """スクラムスクリーンの下地。菱形のタイルを灰色の濃淡とガラスで塗り分ける(面は X 一定)。"""
    m = _principled("scrum_tiles", (0.4, 0.4, 0.4, 1), rough=0.45)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Position"], sep.inputs[0])

    def math(op, a, bval=None, b_sock=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        L.new(a, n.inputs[0])
        if b_sock is not None:
            L.new(b_sock, n.inputs[1])
        elif bval is not None:
            n.inputs[1].default_value = bval
        return n.outputs[0]
    yy = math("DIVIDE", sep.outputs["Y"], 1.6)
    zz = math("DIVIDE", sep.outputs["Z"], 3.0)
    a = math("ADD", yy, b_sock=zz)
    bb = math("SUBTRACT", yy, b_sock=zz)
    fa, fb = math("FLOOR", a), math("FLOOR", bb)
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(fa, comb.inputs[0]); L.new(fb, comb.inputs[1])
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "2D"
    L.new(comb.outputs[0], wn.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position = 0.0; els[0].color = (0.035, 0.045, 0.055, 1)
    els[1].position = 0.14; els[1].color = srgb(128, 132, 138)
    for pos, col in ((0.42, srgb(168, 170, 172)), (0.7, srgb(200, 201, 200)), (0.9, srgb(226, 226, 222))):
        e = els.new(pos); e.color = col
    L.new(wn.outputs["Value"], ramp.inputs["Fac"])
    # 目地
    fra, frb = math("FRACT", a), math("FRACT", bb)
    mn = math("MINIMUM", fra, b_sock=frb)
    joint = math("GREATER_THAN", mn, 0.035)
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    L.new(ramp.outputs["Color"], mul.inputs["A"])
    jc = N.new("ShaderNodeMapRange")
    jc.inputs["To Min"].default_value = 0.45
    L.new(joint, jc.inputs["Value"])
    L.new(jc.outputs["Result"], mul.inputs["B"])
    L.new(mul.outputs["Result"], b.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange")
    rr.inputs["From Max"].default_value = 0.14
    rr.inputs["To Min"].default_value = 0.08
    rr.inputs["To Max"].default_value = 0.5
    L.new(wn.outputs["Value"], rr.inputs["Value"])
    L.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m


def _brick_paving():
    m = _principled("paving_brick", srgb(140, 92, 76), rough=0.9)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")
    br = N.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = srgb(146, 96, 78)
    br.inputs["Color2"].default_value = srgb(126, 82, 70)
    br.inputs["Mortar"].default_value = srgb(96, 78, 70)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 0.42
    br.inputs["Row Height"].default_value = 0.21
    L.new(geo.outputs["Position"], br.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.08
    L.new(geo.outputs["Position"], noise.inputs["Vector"])
    mp = N.new("ShaderNodeMapRange")
    mp.inputs["To Min"].default_value = 0.8
    mp.inputs["To Max"].default_value = 1.15
    L.new(noise.outputs["Fac"], mp.inputs["Value"])
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    L.new(br.outputs["Color"], mul.inputs["A"])
    L.new(mp.outputs["Result"], mul.inputs["B"])
    L.new(mul.outputs["Result"], b.inputs["Base Color"])
    return m


_builders = {
    "scrum_tiles": _scrum_tiles,
    "ground_far": _noisy("ground_far", srgb(120, 124, 118), 0.95, scale=0.004, amount=0.2),
    "turf2": _noisy("turf2", srgb(40, 96, 50), 0.9, scale=0.2, amount=0.12),
    "hockey": _noisy("hockey", srgb(96, 160, 150), 0.85, scale=0.2, amount=0.06),
    "asphalt_dark": _noisy("asphalt_dark", srgb(66, 66, 70), 0.95, scale=0.5, amount=0.15),
    "leaf_a": _noisy("leaf_a", srgb(52, 92, 40), 0.9, scale=1.5, amount=0.35),
    "leaf_b": _noisy("leaf_b", srgb(70, 108, 46), 0.9, scale=1.5, amount=0.35),
    "mountain": _noisy("mountain", srgb(86, 110, 118), 1.0, scale=0.004, amount=0.15),
    "grass": _grass,
    "concrete": _noisy("concrete", srgb(150, 148, 142), 0.85, scale=0.8, amount=0.10, bump=0.15),
    "concrete_dark": _noisy("concrete_dark", srgb(72, 72, 74), 0.9, scale=0.8, amount=0.12, bump=0.15),
    "concrete_light": _noisy("concrete_light", srgb(186, 184, 178), 0.8, scale=0.8, amount=0.07, bump=0.1),
    "asphalt": _noisy("asphalt", srgb(92, 92, 94), 0.95, scale=0.5, amount=0.15, bump=0.2),
    "paving_brick": _brick_paving,
    "paving_brick_plain": _noisy("paving_brick", srgb(140, 92, 76), 0.9, scale=0.6, amount=0.12, bump=0.15),
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
define("seat_red", color=srgb(200, 22, 16), rough=0.6, spec=0.3)
define("seat_blue", color=srgb(20, 48, 160), rough=0.6, spec=0.3)
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
define("tower_pole", color=srgb(40, 36, 34), rough=0.55, metal=0.2)
define("flag_a", color=srgb(240, 240, 240), rough=0.7)
define("flag_b", color=srgb(30, 70, 160), rough=0.7)
define("flag_c", color=srgb(150, 30, 50), rough=0.7)
define("flag_d", color=srgb(40, 130, 70), rough=0.7)
define("sign_white", color=srgb(240, 240, 236), rough=0.5)
define("sign_blue", color=srgb(20, 90, 170), rough=0.5)
define("sign_green", color=srgb(30, 120, 80), rough=0.5)
define("sign_yellow", color=srgb(240, 200, 40), rough=0.5)
define("sign_red", color=srgb(200, 40, 40), rough=0.5)
define("sign_navy", color=srgb(20, 30, 70), rough=0.5)
define("text_dark", color=srgb(20, 22, 30), rough=0.6)
define("text_white", color=srgb(245, 245, 245), rough=0.6)
define("text_red", color=srgb(200, 30, 36), rough=0.6)
define("scrum_dark", color=srgb(84, 90, 100), rough=0.5)
define("scrum_light", color=srgb(224, 226, 226), rough=0.5)
define("trunk", color=srgb(80, 62, 48), rough=0.9)
define("house_a", color=srgb(214, 208, 196), rough=0.9)
define("house_b", color=srgb(188, 186, 180), rough=0.9)
define("house_c", color=srgb(226, 222, 212), rough=0.9)
define("roof_a", color=srgb(78, 82, 92), rough=0.8)
define("roof_b", color=srgb(60, 88, 130), rough=0.8)
define("roof_c", color=srgb(120, 96, 84), rough=0.8)
define("aisle_dark", color=srgb(46, 46, 50), rough=0.9)
