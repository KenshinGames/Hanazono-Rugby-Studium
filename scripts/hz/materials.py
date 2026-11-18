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


def dn_value(nt, day, night, tag=""):
    """昼と夜で値が変わる Value ノードを作り、出力を返す。sky.py がラベル "dn 昼 夜" を見て切り替える。"""
    v = nt.nodes.new("ShaderNodeValue")
    v.label = "dn %g %g %s" % (day, night, tag)
    v.outputs[0].default_value = day
    return v.outputs[0]


def _rainbow(name, base, night=1.1):
    """スクラムスクリーンの斜めの帯。夜は位置ごとに色の変わる虹色に光る(写真から)。"""
    def build():
        m = _principled(name, base, rough=0.5)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(geo.outputs["Position"], sep.inputs[0])
        # 南の弧の中心(-66, 0)から見た角度で色相を決める。正面の 70° ほどで虹を 1 周弱
        dx = N.new("ShaderNodeMath"); dx.operation = "SUBTRACT"
        dx.inputs[0].default_value = -66.0
        L.new(sep.outputs["X"], dx.inputs[1])            # -66 - x (外側が正)
        at = N.new("ShaderNodeMath"); at.operation = "ARCTAN2"
        L.new(sep.outputs["Y"], at.inputs[0]); L.new(dx.outputs[0], at.inputs[1])
        hu = N.new("ShaderNodeMath"); hu.operation = "MULTIPLY_ADD"
        hu.inputs[1].default_value = 0.015 * 57.29578
        hu.inputs[2].default_value = 0.30
        L.new(at.outputs[0], hu.inputs[0])
        # 高さでも少し色をずらす(帯の中で色がにじんで見える)
        hz_ = N.new("ShaderNodeMath"); hz_.operation = "MULTIPLY_ADD"
        hz_.inputs[1].default_value = 0.006
        L.new(sep.outputs["Z"], hz_.inputs[0]); L.new(hu.outputs[0], hz_.inputs[2])
        fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"
        L.new(hz_.outputs[0], fr.inputs[0])
        cc = N.new("ShaderNodeCombineColor"); cc.mode = "HSV"
        cc.inputs[1].default_value = 1.0
        cc.inputs[2].default_value = 1.0
        L.new(fr.outputs[0], cc.inputs[0])
        L.new(cc.outputs[0], b.inputs["Emission Color"])
        L.new(dn_value(nt, 0.0, night, "rainbow"), b.inputs["Emission Strength"])
        return m
    return build


def _house_wall(name, color):
    """家やマンションの壁。窓の格子を描き、夜は 3 割ほどの窓に明かりがともる。"""
    def build():
        m = _principled(name, color, rough=0.9)
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        b = N.get("Principled BSDF")
        geo = N.new("ShaderNodeNewGeometry")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(geo.outputs["Position"], sep.inputs[0])

        def mth(op, a, v=None, bs=None):
            n = N.new("ShaderNodeMath"); n.operation = op
            L.new(a, n.inputs[0])
            if bs is not None:
                L.new(bs, n.inputs[1])
            elif v is not None:
                n.inputs[1].default_value = v
            return n.outputs[0]
        h = mth("DIVIDE", mth("ADD", sep.outputs["X"], bs=sep.outputs["Y"]), 2.6)
        zz = mth("DIVIDE", sep.outputs["Z"], 3.0)
        fh, fz = mth("FRACT", h), mth("FRACT", zz)
        inside = mth("MULTIPLY", mth("MULTIPLY", mth("GREATER_THAN", fh, 0.25), bs=mth("LESS_THAN", fh, 0.75)),
                     bs=mth("MULTIPLY", mth("GREATER_THAN", fz, 0.35), bs=mth("LESS_THAN", fz, 0.78)))
        win = mth("MULTIPLY", inside, bs=mth("GREATER_THAN", sep.outputs["Z"], 0.8))
        comb = N.new("ShaderNodeCombineXYZ")
        L.new(mth("FLOOR", h), comb.inputs[0]); L.new(mth("FLOOR", zz), comb.inputs[1])
        L.new(mth("FLOOR", mth("DIVIDE", mth("SUBTRACT", sep.outputs["X"], bs=sep.outputs["Y"]), 7.0)), comb.inputs[2])
        wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
        L.new(comb.outputs[0], wn.inputs["Vector"])
        lit = mth("MULTIPLY", win, bs=mth("LESS_THAN", wn.outputs["Value"], 0.32))
        # 昼: 窓は暗いガラスに
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
        mx.inputs["A"].default_value = color
        mx.inputs["B"].default_value = (0.05, 0.06, 0.07, 1)
        L.new(mth("MULTIPLY", win, 0.75), mx.inputs["Factor"])
        L.new(mx.outputs["Result"], b.inputs["Base Color"])
        # 夜: 暖かい色と白っぽい色の明かり
        wc = N.new("ShaderNodeMix"); wc.data_type = "RGBA"
        wc.inputs["A"].default_value = (1.0, 0.72, 0.42, 1)
        wc.inputs["B"].default_value = (0.92, 0.95, 1.0, 1)
        L.new(mth("GREATER_THAN", wn.outputs["Value"], 0.2), wc.inputs["Factor"])
        ec = N.new("ShaderNodeMix"); ec.data_type = "RGBA"
        ec.inputs["A"].default_value = (0, 0, 0, 1)
        L.new(lit, ec.inputs["Factor"]); L.new(wc.outputs["Result"], ec.inputs["B"])
        L.new(ec.outputs["Result"], b.inputs["Emission Color"])
        L.new(dn_value(nt, 0.0, 3.0, "windows"), b.inputs["Emission Strength"])
        return m
    return build


HAZE_START = 220.0      # ここまでは霞まない(スタジアムのまわり)
HAZE_SCALE = 2600.0     # これだけ離れると 6 割ほど霞む


def add_haze(m):
    """遠くの物ほど空の色に溶かす(空気遠近)。マテリアルの出力の手前に混ぜる。"""
    if not m.use_nodes or m.get("hazed"):
        return
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    out = next((n for n in N if n.type == "OUTPUT_MATERIAL"), None)
    if out is None or not out.inputs["Surface"].links:
        return
    src = out.inputs["Surface"].links[0].from_socket
    cam = N.new("ShaderNodeCameraData")
    d = N.new("ShaderNodeMath"); d.operation = "SUBTRACT"
    L.new(cam.outputs["View Distance"], d.inputs[0]); d.inputs[1].default_value = HAZE_START
    d2 = N.new("ShaderNodeMath"); d2.operation = "MAXIMUM"
    L.new(d.outputs[0], d2.inputs[0]); d2.inputs[1].default_value = 0.0
    d3 = N.new("ShaderNodeMath"); d3.operation = "DIVIDE"
    L.new(d2.outputs[0], d3.inputs[0]); d3.inputs[1].default_value = -HAZE_SCALE
    e = N.new("ShaderNodeMath"); e.operation = "EXPONENT"
    L.new(d3.outputs[0], e.inputs[0])
    f = N.new("ShaderNodeMath"); f.operation = "SUBTRACT"
    f.inputs[0].default_value = 1.0; L.new(e.outputs[0], f.inputs[1])
    f2 = N.new("ShaderNodeMath"); f2.operation = "MULTIPLY"
    L.new(f.outputs[0], f2.inputs[0])
    L.new(dn_value(nt, 0.92, 0.85, "haze_max"), f2.inputs[1])
    col = N.new("ShaderNodeMix"); col.data_type = "RGBA"
    col.inputs["A"].default_value = HAZE_DAY
    col.inputs["B"].default_value = HAZE_NIGHT
    L.new(dn_value(nt, 0.0, 1.0, "haze_col"), col.inputs["Factor"])
    em = N.new("ShaderNodeEmission")
    L.new(col.outputs["Result"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    ms = N.new("ShaderNodeMixShader")
    L.new(f2.outputs[0], ms.inputs[0])
    L.new(src, ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], out.inputs["Surface"])
    m["hazed"] = 1


import os as _os
HAZE_DAY = tuple(float(v) for v in _os.environ.get("HZ_HAZE", "0.50,0.58,0.70").split(",")) + (1.0,)
HAZE_NIGHT = (0.018, 0.028, 0.062, 1.0)


def haze_all():
    for m in list(_cache.values()):
        add_haze(m)


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
    ramp.inputs["A"].default_value = (0.030, 0.088, 0.008, 1)
    ramp.inputs["B"].default_value = (0.042, 0.118, 0.011, 1)
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
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.04
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
    yy = math("DIVIDE", sep.outputs["Y"], 0.8)
    zz = math("DIVIDE", sep.outputs["Z"], 1.6)
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
    els[1].position = 0.26; els[1].color = srgb(96, 102, 110)
    for pos, col in ((0.5, srgb(132, 136, 140)), (0.74, srgb(166, 168, 170)), (0.92, srgb(200, 200, 198))):
        e = els.new(pos); e.color = col
    # 白い乱数に高さを混ぜて、下ほど暗いガラス・上ほど明るいタイルが規則的に並ぶようにする
    zn = math("DIVIDE", sep.outputs["Z"], 23.6)
    mix_v = N.new("ShaderNodeMix"); mix_v.data_type = "FLOAT"
    mix_v.inputs["Factor"].default_value = 0.5
    L.new(wn.outputs["Value"], mix_v.inputs["A"])
    L.new(zn, mix_v.inputs["B"])
    # 階の高さ(4.5〜8.5 m、11〜14 m)はガラスの帯
    b1 = math("MULTIPLY", math("GREATER_THAN", sep.outputs["Z"], 4.5), b_sock=math("LESS_THAN", sep.outputs["Z"], 8.5))
    b2 = math("MULTIPLY", math("GREATER_THAN", sep.outputs["Z"], 11.0), b_sock=math("LESS_THAN", sep.outputs["Z"], 14.0))
    band = math("MULTIPLY", math("ADD", b1, b_sock=b2), 0.22)
    vv = math("SUBTRACT", mix_v.outputs["Result"], b_sock=band)
    L.new(vv, ramp.inputs["Fac"])
    # 夜はガラスのタイルに中の明かりがともる
    glass = math("MULTIPLY", math("LESS_THAN", vv, 0.26), b_sock=math("ADD", b1, b_sock=b2))
    em = N.new("ShaderNodeMix"); em.data_type = "RGBA"
    em.inputs["A"].default_value = (0, 0, 0, 1)
    em.inputs["B"].default_value = (0.95, 0.92, 0.85, 1)
    L.new(glass, em.inputs["Factor"])
    L.new(em.outputs["Result"], b.inputs["Emission Color"])
    L.new(dn_value(nt, 0.0, 1.3, "tiles"), b.inputs["Emission Strength"])
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
    rr.inputs["From Max"].default_value = 0.26
    rr.inputs["To Min"].default_value = 0.08
    rr.inputs["To Max"].default_value = 0.5
    L.new(vv, rr.inputs["Value"])
    L.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m


def _mountain():
    """遠くの山の森。常緑の濃い緑に落葉樹の茶色を混ぜ、谷(すき間)を暗くして、正面から日が当たっても尾根と谷が見えるようにする。"""
    m = _principled("mountain", srgb(36, 60, 36), rough=1.0, spec=0.2)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    geo = N.new("ShaderNodeNewGeometry")

    def noise(scale, detail):
        n = N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        L.new(geo.outputs["Position"], n.inputs["Vector"])
        return n.outputs["Fac"]

    def rng(src, lo, hi, f0=0.0, f1=1.0):
        mp = N.new("ShaderNodeMapRange")
        mp.inputs["From Min"].default_value = f0
        mp.inputs["From Max"].default_value = f1
        mp.inputs["To Min"].default_value = lo
        mp.inputs["To Max"].default_value = hi
        L.new(src, mp.inputs["Value"])
        return mp.outputs["Result"]

    def mul(a, bsock):
        n = N.new("ShaderNodeMix"); n.data_type = "RGBA"; n.blend_type = "MULTIPLY"
        n.inputs["Factor"].default_value = 1.0
        L.new(a, n.inputs["A"]); L.new(bsock, n.inputs["B"])
        return n.outputs["Result"]
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = srgb(34, 58, 34)
    mix.inputs["B"].default_value = srgb(80, 72, 44)
    L.new(rng(noise(0.012, 4.0), 0.0, 0.6, 0.45, 0.7), mix.inputs["Factor"])
    col = mul(mix.outputs["Result"], rng(noise(0.0025, 6.0), 0.6, 1.4))
    col = mul(col, rng(noise(0.03, 3.0), 0.7, 1.3))
    ao = N.new("ShaderNodeAmbientOcclusion")
    ao.samples = 8
    ao.inputs["Distance"].default_value = 220.0
    col = mul(col, rng(ao.outputs["AO"], 0.15, 1.0))
    L.new(col, b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    bp.inputs["Distance"].default_value = 4.0
    L.new(noise(0.05, 3.0), bp.inputs["Height"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])
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
    "scrum_dark": _rainbow("scrum_dark", srgb(62, 70, 84)),
    "scrum_light": _rainbow("scrum_light", srgb(196, 199, 202), night=0.0),
    "house_a": _house_wall("house_a", srgb(168, 162, 150)),
    "house_b": _house_wall("house_b", srgb(146, 144, 138)),
    "house_c": _house_wall("house_c", srgb(182, 176, 164)),
    "apart_a": _house_wall("apart_a", srgb(198, 194, 184)),
    "apart_b": _house_wall("apart_b", srgb(156, 150, 140)),
    "ground_far": _noisy("ground_far", srgb(104, 110, 102), 0.95, scale=0.004, amount=0.2),
    "turf2": _noisy("turf2", srgb(40, 96, 50), 0.9, scale=0.2, amount=0.12),
    "hockey": _noisy("hockey", srgb(96, 160, 150), 0.85, scale=0.2, amount=0.06),
    "asphalt_dark": _noisy("asphalt_dark", srgb(66, 66, 70), 0.95, scale=0.5, amount=0.15),
    "leaf_a": _noisy("leaf_a", srgb(52, 92, 40), 0.9, scale=1.5, amount=0.35),
    "leaf_b": _noisy("leaf_b", srgb(70, 108, 46), 0.9, scale=1.5, amount=0.35),
    "mountain": _mountain,
    "grass": _grass,
    "concrete": _noisy("concrete", srgb(150, 148, 142), 0.85, scale=0.8, amount=0.10, bump=0.15),
    "concrete_dark": _noisy("concrete_dark", srgb(72, 72, 74), 0.9, scale=0.8, amount=0.12, bump=0.15),
    "concrete_light": _noisy("concrete_light", srgb(186, 184, 178), 0.8, scale=0.8, amount=0.07, bump=0.1),
    "asphalt": _noisy("asphalt", srgb(92, 92, 94), 0.95, scale=0.5, amount=0.15, bump=0.2),
    "paving_brick": _brick_paving,
    "paving_brick_plain": _noisy("paving_brick", srgb(140, 92, 76), 0.9, scale=0.6, amount=0.12, bump=0.15),
    "paving_grey": _noisy("paving_grey", srgb(170, 168, 162), 0.9, scale=0.6, amount=0.10, bump=0.15),
    "apron": _noisy("apron", srgb(18, 86, 40), 0.9, scale=2.0, amount=0.10, bump=0.3),
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
define("tv_tower", color=srgb(196, 190, 184), rough=0.5)
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
define("trunk", color=srgb(80, 62, 48), rough=0.9)
define("roof_a", color=srgb(62, 66, 74), rough=0.8)
define("roof_b", color=srgb(58, 76, 104), rough=0.8)
define("roof_c", color=srgb(98, 80, 72), rough=0.8)
define("aisle_dark", color=srgb(46, 46, 50), rough=0.9)
define("factory_roof", color=srgb(120, 132, 140), rough=0.5, metal=0.4)
define("factory_wall", color=srgb(176, 178, 176), rough=0.8)
define("rail", color=srgb(120, 110, 100), rough=0.4, metal=0.8)
define("ballast", color=srgb(110, 104, 96), rough=1.0)
define("train_body", color=srgb(220, 222, 224), rough=0.4)
