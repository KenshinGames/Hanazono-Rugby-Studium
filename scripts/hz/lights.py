"""⑥照明: 四隅の照明塔、メインスタンド屋根の先端の投光器、夜に光らせる光源。"""
import math

import bpy
from mathutils import Vector

from . import config, layout, materials as M, roof
from .details import rail_u
from .util import MB, coll, frame_xf

LAMP_COLOR = (1.0, 0.96, 0.90, 1.0)


def _lens():
    return M.emissive("lamp_lens", LAMP_COLOR, 0.0, 90.0, base=(0.75, 0.76, 0.74, 1.0))


def _area(name, c, loc, direction, w, h, energy, spread=120.0):
    li = bpy.data.lights.new(name, "AREA")
    li.shape = "RECTANGLE"
    li.size = w
    li.size_y = h
    li.energy = energy
    li.color = LAMP_COLOR[:3]
    li.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    ob.visible_camera = False
    c.objects.link(ob)
    return ob


def build():
    cfg = config.load()
    c = coll("lights")
    nc = coll("night_lights")
    _towers(cfg, c, nc)
    _roof_lamps(cfg, c, nc)


def _towers(cfg, c, nc):
    T = cfg["towers"]
    pole = M.get("tower_pole")
    dark = M.get("dark_steel")
    lens = _lens()
    H = T["height"]
    bw, bh = T["bank_w"], T["bank_h"]
    for tag, (x, y) in T["positions"].items():
        mb = MB()
        zc = H - bh / 2
        mb.cyl((x, y, 0), (x, y, zc + 0.8), T["pole_r_bottom"], pole, n=24, r1=T["pole_r_top"], caps=True)
        # 枠はフィールドの中心より少し手前を向く(下向きに傾く)
        aim = Vector((x * 0.15, y * 0.15, 0.0))
        horiz = Vector((aim.x - x, aim.y - y, 0)).normalized()
        centre = Vector((x, y, zc)) + horiz * 1.2
        n = (aim - centre).normalized()
        n = (horiz * math.cos(math.radians(14)) + Vector((0, 0, -1)) * math.sin(math.radians(14))).normalized()
        mb.xf = frame_xf(centre, n)
        rows, cols = T["rows"], T["cols"]
        # 枠
        for yy in (-bh / 2, bh / 2):
            mb.bar((-bw / 2, yy, -0.25), (bw / 2, yy, -0.25), 0.14, 0.14, dark)
        for i in range(7):
            xx = -bw / 2 + bw * i / 6
            mb.bar((xx, -bh / 2, -0.25), (xx, bh / 2, -0.25), 0.12, 0.12, dark)
        for r in range(rows):
            yy = -bh / 2 + bh * (r + 0.5) / rows
            mb.bar((-bw / 2, yy - 0.42, -0.2), (bw / 2, yy - 0.42, -0.2), 0.08, 0.08, dark)
            # 点検用の足場
            mb.box(-bw / 2, bw / 2, yy - 0.62, yy - 0.56, -1.0, -0.3, dark)
            for k in range(cols):
                xx = -bw / 2 + bw * (k + 0.5) / cols
                mb.box(xx - 0.36, xx + 0.36, yy - 0.30, yy + 0.30, -0.15, 0.32, dark)
                mb.face(((xx - 0.31, yy - 0.25, 0.325), (xx + 0.31, yy - 0.25, 0.325),
                         (xx + 0.31, yy + 0.25, 0.325), (xx - 0.31, yy + 0.25, 0.325)), lens)
        # 柱の頭と枠をつなぐ腕、避雷針
        for xx in (-bw * 0.3, 0.0, bw * 0.3):
            mb.bar((0, -0.5, -1.2), (xx, 0, -0.25), 0.16, 0.16, dark)
        for xx in (-bw * 0.36, bw * 0.36):
            mb.cyl((xx, bh / 2, -0.25), (xx, bh / 2 + 2.6, -0.25), 0.03, dark, n=5)
        mb.build("tower_" + tag, c)
        # 夜の光: 枠の前に面の光を 1 枚
        aim2 = Vector((x * 0.25, y * 0.2, 0.0))
        loc = centre + n * 1.0
        _area("tower_light_" + tag, nc, loc, (aim2 - loc), bw, bh, 9.0e4, spread=100.0)


def _roof_lamps(cfg, c, nc):
    R = cfg["roof"]
    T = cfg["towers"]
    xfw = layout.xf("west")
    dark = M.get("dark_steel")
    lens = _lens()
    mb = MB(xfw)
    u0, u1 = R["main"]["u0"] + 1.0, R["north"]["u1"] - 1.0
    d = R["main"]["d0"] - 0.1
    z = roof.z_top(R, d) + 0.25
    # 先端の上の点検通路と手すり
    mb.box(u0 - 0.5, u1 + 0.5, d + 0.5, d + 1.5, z, z + 0.06, M.get("grey_steel"))
    rail_u(mb, u0 - 0.5, u1 + 0.5, d + 1.5, z, h=1.1, mat=M.get("white_steel"), post=2.0)
    mb.bar((u0 - 0.5, d + 0.15, z + 0.75), (u1 + 0.5, d + 0.15, z + 0.75), 0.1, 0.1, M.get("white_steel"))
    n = T["roof_lamps"]
    nrm = Vector((0, -math.cos(math.radians(38)), -math.sin(math.radians(38))))
    for i in range(n):
        u = u0 + (u1 - u0) * i / (n - 1)
        if i % 8 == 0:
            mb.xf = xfw
            mb.bar((u, d + 0.15, z), (u, d + 0.15, z + 0.75), 0.07, 0.07, M.get("white_steel"))
        mb.xf = xfw @ frame_xf((u, d + 0.05, z + 0.8), nrm)
        mb.box(-0.3, 0.3, -0.26, 0.26, -0.3, 0.12, dark)
        mb.face(((-0.26, -0.22, 0.125), (0.26, -0.22, 0.125), (0.26, 0.22, 0.125), (-0.26, 0.22, 0.125)), lens)
    mb.build("roof_lamps", c)
    # 夜の光: 先端に沿って面の光を並べる
    k = 7
    for i in range(k):
        u = u0 + (u1 - u0) * (i + 0.5) / k
        loc = xfw @ Vector((u, d - 0.6, z + 0.6))
        tgt = Vector((u * 0.7, 5.0, 0.0))
        _area("roof_light_%d" % i, nc, loc, tgt - loc, (u1 - u0) / k * 0.9, 0.5, 2.2e4, spread=110.0)
