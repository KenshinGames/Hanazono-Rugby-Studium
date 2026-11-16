"""⑤細部: 縦通路の段、出入口の箱、手すり、北スタンド下のガラスの部屋、メインスタンドの前の壁の出入口。"""
import math

from . import config, layout, materials as M, stands
from .util import MB, coll


def rail_u(mb, u0, u1, d, z, h=1.1, mat=None, post=1.5):
    """u 方向の手すり(支柱、笠木、中桟)。"""
    mat = mat or M.get("aluminium")
    if u1 - u0 < 0.3:
        return
    n = max(1, round((u1 - u0) / post))
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        mb.cyl((u, d, z), (u, d, z + h), 0.022, mat, n=6)
    mb.cyl((u0, d, z + h), (u1, d, z + h), 0.028, mat, n=6)
    mb.cyl((u0, d, z + h * 0.5), (u1, d, z + h * 0.5), 0.016, mat, n=5)


def build():
    c = coll("details")
    sc = config.load()["seats"]
    for name in ("west", "east", "north", "south"):
        st = layout.stand(name)
        xf = layout.xf(name)
        T = layout.treads(st)
        V = layout.voms(st)
        A = layout.aisles(st)
        w = sc["aisle_w"]

        # 縦通路: 暗い色の帯と、蹴上げを半分に割る小段
        mb = MB(xf)
        dark = M.get("aisle_dark")
        for t in T:
            if t["kind"] != "row":
                continue
            a, b = layout.u_range(st, t["d0"])
            lanes = [(u - w / 2, u + w / 2) for u in A[1:-1]]
            lanes += [(a, a + sc["edge_w"]), (b - sc["edge_w"], b)]
            for (l0, l1) in lanes:
                um = (l0 + l1) / 2
                if any(v["u0"] - 0.3 < um < v["u1"] + 0.3 and v["d0"] - 1e-6 <= t["d0"] < v["d1"] - 1e-6 for v in V):
                    continue
                mb.rect(l0, l1, t["d0"], t["d1"] - 0.4, t["z"] + 0.006, dark)
                mb.box(l0, l1, t["d1"] - 0.4, t["d1"], t["z"], t["z"] + t["riser"] / 2, dark, bottom=False)
        mb.build("aisles_" + name, c)

        # 出入口の箱
        mb = MB(xf)
        white = M.get("white_paint")
        for v in V:
            for (x0, x1) in ((v["u0"] - 0.2, v["u0"]), (v["u1"], v["u1"] + 0.2)):
                mb.box(x0, x1, v["d0"], v["d1"], v["zf"], v["ztop"], white)
            mb.box(v["u0"] - 0.2, v["u1"] + 0.2, v["d1"] - 0.2, v["d1"], v["zf"], v["ztop"], white)
            mb.rect(v["u0"], v["u1"], v["d0"], v["d1"] - 0.2, v["zf"] + 0.01, M.get("concrete"))
            mb.box(v["u0"] + 0.35, v["u1"] - 0.35, v["d1"] - 0.23, v["d1"] - 0.2, v["zf"], v["zf"] + 2.2, M.get("black"))
        if not mb.empty():
            mb.build("voms_" + name, c)

        # 手すり: 前の壁の上、横通路の前
        mb = MB(xf)
        a, b = layout.u_range(st, 0.15)
        rail_u(mb, a + 0.1, b - 0.1, 0.15, st["front_wall_h"])
        flats = [t for t in T if t["kind"] == "flat"]
        for t in flats[1:-1] if T[0]["kind"] == "flat" else flats[:-1]:
            a, b = layout.u_range(st, t["d0"])
            cuts = [(u - w / 2, u + w / 2) for u in A[1:-1]]
            for (x0, x1) in layout.subtract(a + sc["edge_w"], b - sc["edge_w"], cuts):
                rail_u(mb, x0 + 0.05, x1 - 0.05, t["d0"] + 0.08, t["z"], h=1.0)
        mb.build("rails_" + name, c, smooth=True)

    _north_glass(c)
    _west_wall(c)
    _corner_rails(c)


def _north_glass(c):
    st = layout.stand("north")
    mb = MB(layout.xf("north"))
    a, b = layout.u_range(st, 0.0)
    h = st["front_wall_h"]
    n = 9
    bay = (b - a) / n
    white = M.get("white_paint")
    for i in range(n + 1):
        u = a + bay * i
        mb.box(u - 0.3, u + 0.3, -0.28, 0.0, 0.0, h, white)
    for i in range(n):
        u0, u1 = a + bay * i + 0.3, a + bay * (i + 1) - 0.3
        mb.box(u0, u1, -0.05, 0.0, 0.25, h - 1.0, M.get("glass"))
        k = 5
        for j in range(1, k):
            u = u0 + (u1 - u0) * j / k
            mb.box(u - 0.04, u + 0.04, -0.1, -0.05, 0.25, h - 1.0, M.get("aluminium"))
        mb.box(u0, u1, -0.1, -0.05, h - 1.05, h - 0.95, M.get("aluminium"))
        mb.box(u0, u1, -0.1, 0.0, 0.0, 0.25, white)
    mb.box(a - 0.3, b + 0.3, -0.35, 0.0, h - 0.5, h + 0.25, white)
    mb.build("north_glass", c)


def _west_wall(c):
    st = layout.stand("west")
    mb = MB(layout.xf("west"))
    blk = M.get("black")
    grey = M.get("grey_steel")
    # 中央の選手の出入口と、両脇の扉
    mb.box(-2.6, 2.6, -0.04, 0.0, 0.0, 2.7, blk)
    for u in (-52, -38, -27, 27, 38, 52, 64):
        mb.box(u - 0.9, u + 0.9, -0.04, 0.0, 0.0, 2.1, grey)
    mb.box(st["u0"][0], st["u1"][0], -0.06, 0.0, st["front_wall_h"] - 0.12, st["front_wall_h"] + 0.05, M.get("concrete"))
    mb.build("west_wall_details", c)


def _corner_rails(c):
    k = config.load()["stands"]["corners"]
    steps = stands.corner_steps()
    al = M.get("aluminium")
    for sy, tag in ((1, "sw"), (-1, "se")):
        mb = MB()
        cx, cy = k["cx"], sy * k["cy"]
        a0, a1 = (90.0, 180.0) if sy > 0 else (-180.0, -90.0)

        def arc_rail(r, z, h, a_from, a_to):
            n = max(2, int(abs(a_to - a_from) / 360 * 2 * math.pi * r / 1.5))
            prev = None
            for i in range(n + 1):
                a = math.radians(a_from + (a_to - a_from) * i / n)
                p = (cx + r * math.cos(a), cy + r * math.sin(a))
                mb.cyl((p[0], p[1], z), (p[0], p[1], z + h), 0.025, al, n=6)
                if prev:
                    mb.cyl((prev[0], prev[1], z + h), (p[0], p[1], z + h), 0.03, al, n=6)
                    mb.cyl((prev[0], prev[1], z + h * 0.5), (p[0], p[1], z + h * 0.5), 0.018, al, n=5)
                prev = p

        arc_rail(steps[0][0] + 0.12, steps[0][2], 1.1, a0, a1)
        # 立見の段のあいだの手すり(弧を切れ切れに)
        for si in (5, 10, 15, 20):
            r0, r1, z = steps[si]
            nseg = 7
            for j in range(nseg):
                s0 = a0 + (a1 - a0) * (j + 0.12) / nseg
                s1 = a0 + (a1 - a0) * (j + 0.88) / nseg
                arc_rail(r0 + 0.1, z, 1.05, s0, s1)
        mb.build("corner_rails_" + tag, c, smooth=True)
